"""
Copyright 2019 Goldman Sachs.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
import asyncio
import base64
import datetime as dt
import json
import logging
import math
import os
import sys
import time
from socket import gaierror
from typing import Iterable, Optional, Union

import msgpack
from opentracing import Span

from gs_quant.api.risk import RiskApi
from gs_quant.risk import RiskRequest
from gs_quant.target.risk import OptimizationRequest
from gs_quant.tracing import Tracer

_logger = logging.getLogger(__name__)


class WebsocketUnavailable(Exception):
    pass


class GsRiskApi(RiskApi):
    USE_MSGPACK = True
    POLL_FOR_BATCH_RESULTS = False

    @classmethod
    def calc_multi(cls, requests: Iterable[RiskRequest]) -> dict:
        requests = tuple(requests)
        results = cls._exec(requests)

        if len(results) < len(requests):
            results = [RuntimeError('Missing results')] * len(requests)

        return dict(zip(requests, results))

    @classmethod
    def calc(cls, request: RiskRequest) -> Iterable:
        return cls._exec(request)

    @classmethod
    def _exec(cls, request: Union[RiskRequest, Iterable[RiskRequest]]) -> Union[Iterable, dict]:
        use_msgpack = cls.USE_MSGPACK and not isinstance(request, RiskRequest)
        headers = {'Content-Type': 'application/x-msgpack'} if use_msgpack else {}
        result, request_id = cls.get_session()._post(cls.__url(request),
                                                     request,
                                                     request_headers=headers,
                                                     timeout=181,
                                                     return_request_id=True)

        for sub_request in request:
            sub_request._id = request_id

        return result

    @classmethod
    def __url(cls, request: Union[RiskRequest, Iterable[RiskRequest]]):
        is_bulk = not isinstance(request, RiskRequest)
        return '/risk/calculate{}'.format('/bulk' if is_bulk else '')

    @classmethod
    async def get_results(cls, responses: asyncio.Queue, results: asyncio.Queue,
                          timeout: Optional[int] = None, span: Optional[Span] = None) -> Optional[str]:
        if cls.POLL_FOR_BATCH_RESULTS:
            return await cls.__get_results_poll(responses, results, timeout=timeout, span=span)
        else:
            try:
                return await cls.__get_results_ws(responses, results, timeout=timeout, span=span)
            except WebsocketUnavailable:
                return await cls.__get_results_poll(responses, results, timeout=timeout, span=span)

    @classmethod
    async def __get_results_poll(cls, responses: asyncio.Queue, results: asyncio.Queue, timeout: Optional[int] = None,
                                 span: Optional[Span] = None):
        run = True
        pending_requests = {}
        end_time = dt.datetime.now() + dt.timedelta(seconds=timeout) if timeout else None

        if span:
            Tracer.get_instance().scope_manager.activate(span, finish_on_close=False)

        while pending_requests or run:
            # Check for timeout
            if end_time is not None and dt.datetime.now() > end_time:
                _logger.error('Fatal error: timeout while waiting for results')
                cls.shutdown_queue_listener(results)
                return

            shutdown, items = await cls.drain_queue_async(responses, timeout=2)

            if shutdown:
                run = False

            if items:
                # ... update the pending requests ...
                pending_requests.update(((i[1]['reportId'], i[0]) for i in items))

            if not pending_requests:
                continue

            # ... poll for completed requests ...

            try:
                calc_results = cls.get_session()._post('/risk/calculate/results/bulk', list(pending_requests.keys()))

                # ... enqueue the request and result for the listener to handle ...
                for result in calc_results:
                    if 'error' in result:
                        results.put_nowait((pending_requests.pop(result['requestId']), RuntimeError(result['error'])))
                    elif 'result' in result:
                        results.put_nowait((pending_requests.pop(result['requestId']), result['result']))
            except Exception as e:
                error_str = f'Fatal error polling for results: {e}'
                _logger.error(error_str)
                cls.shutdown_queue_listener(results)
                return error_str

    @classmethod
    async def __get_results_ws(cls, responses: asyncio.Queue, results: asyncio.Queue, timeout: Optional[int] = None,
                               span: Optional[Span] = None):
        async def handle_websocket():
            ret = ''

            try:
                # If we're re-connecting then re-send any in-flight request ids

                outstanding_request_ids = [i for i in pending_requests.keys() if i not in dispatched]
                if outstanding_request_ids:
                    _logger.info(f'Re-sending {len(outstanding_request_ids)} requests')
                    await asyncio.wait_for(ws.send(json.dumps(outstanding_request_ids)), timeout=send_timeout)

                all_requests_dispatched = False

                while pending_requests or not all_requests_dispatched:
                    # Continue while we have pending or un-dispatched requests
                    _logger.debug(f'waiting for {", ".join(pending_requests.keys())}')
                    request_listener = asyncio.ensure_future(cls.drain_queue_async(responses)) \
                        if not all_requests_dispatched else None
                    result_listener = asyncio.ensure_future(ws.recv())
                    listeners = tuple(filter(None, (request_listener, result_listener)))

                    # Wait for either a request or result
                    complete, pending = await asyncio.wait(listeners, return_when=asyncio.FIRST_COMPLETED)

                    # Check results before sending more requests. Results can be lost otherwise
                    if result_listener in complete:
                        # New results have been received
                        request_id = None
                        try:
                            request_id, status_result_str = result_listener.result().split(';', 1)
                            status, result_str = status_result_str[0], status_result_str[1:]
                        except Exception as ee:
                            status = 'E'
                            result_str = str(ee)

                        if status == 'E':
                            # An error
                            result = RuntimeError(result_str)
                        else:
                            # Unpack the result
                            try:
                                result = msgpack.unpackb(base64.b64decode(result_str), raw=False) \
                                    if cls.USE_MSGPACK else json.loads(result_str)
                            except Exception as ee:
                                result = ee
                        if request_id is None:
                            # Certain fatal websocket errors (e.g. ConnectionClosed) that are caught above will mean
                            # we have no request_id - In this case we abort and set the error on all results
                            result_listener.cancel()
                            for req in pending_requests.values():
                                results.put_nowait((req, result))
                            # Give up
                            pending_requests.clear()
                            all_requests_dispatched = True
                        else:
                            # Enqueue the request and result for the listener to handle
                            results.put_nowait((pending_requests.pop(request_id), result))
                    else:
                        result_listener.cancel()

                    if request_listener:
                        if request_listener in complete:
                            # New requests have been posted ...

                            all_requests_dispatched, items = request_listener.result()
                            if items:
                                if not all([isinstance(i[1], dict) for i in items]):
                                    error_item = next(i[1] for i in items if not isinstance(i[1], dict))
                                    raise RuntimeError(error_item[0][0][0]['errorString'])

                                # ... extract the request IDs ...
                                request_ids = [i[1]['reportId'] for i in items]

                                # ... update the pending requests ...
                                pending_requests.update(zip(request_ids, (i[0] for i in items)))

                                # ... add to our result subscription ...
                                await asyncio.wait_for(ws.send(json.dumps(request_ids)), timeout=send_timeout)

                                # ... note dispatched
                                dispatched.update(request_ids)
                        else:
                            request_listener.cancel()
            except Exception as ee:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                ret = f'{exc_type} {fname} ln:{exc_tb.tb_lineno}' + str(ee)

            return ret

        pending_requests = {}
        dispatched = set()
        error = ''
        attempts = 0
        max_attempts = 5
        send_timeout = 30

        from websockets import ConnectionClosedError
        while attempts < max_attempts:
            if attempts > 0:
                await asyncio.sleep(math.pow(2, attempts))
                _logger.error(f'{error} error, retrying (attempt {attempts + 1} of {max_attempts})')

            try:
                ws_url = '/risk/calculate/results/subscribe'
                async with cls.get_session()._connect_websocket(ws_url) as ws:
                    if span:
                        Tracer.get_instance().scope_manager.activate(span, finish_on_close=False)
                        with Tracer(f'wss:/{ws_url}') as scope:
                            scope.span.set_tag('wss.host', ws.request_headers.get('host'))
                            error = await handle_websocket()
                    else:
                        error = await handle_websocket()

                attempts = max_attempts
            except ConnectionClosedError as cce:
                error = 'Connection failed: ' + str(cce)
                attempts += 1
            except asyncio.TimeoutError:
                error = 'Timed out'
                attempts = max_attempts
            except gaierror:
                raise WebsocketUnavailable()
            except Exception as e:
                error = str(e)
                attempts = max_attempts

        if error != '':
            _logger.error(f'Fatal error with websocket: {error}')
            cls.shutdown_queue_listener(results)
            return error

    @classmethod
    def create_pretrade_execution_optimization(cls, request: OptimizationRequest) -> str:
        try:
            response = cls.get_session()._post(r'/risk/execution/pretrade', request)
            _logger.info('New optimization is created with id: {}'.format(response.get("optimizationId")))
            return response
        except Exception as e:
            error = str(e)
            _logger.error(error)
            return error

    @classmethod
    def get_pretrade_execution_optimization(cls, optimization_id: str, max_attempts: int = 15):
        url = '/risk/execution/pretrade/{}/results'.format(optimization_id)
        attempts = 0
        start = time.perf_counter()
        results = {}

        while attempts < max_attempts:
            if attempts > 0:
                time.sleep(math.pow(2, attempts))
                _logger.error('Retrying (attempt {} of {})'.format(attempts, max_attempts))
            try:
                results = cls.get_session()._get(url)
                if results.get('status') == 'Running':
                    attempts += 1
                else:
                    break
            except Exception as e:
                error = str(e)
                _logger.error(error)
                return error

        if results.get('status') == 'Running':
            _logger.info('Optimization is still running. Please retry fetching the results.')
            return results
        else:
            _logger.info('Optimization is fetched in {:.3f}s.'.format(time.perf_counter() - start))
            return results
