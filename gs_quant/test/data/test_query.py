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
import datetime

from gs_quant.api.gs.data import GsDataApi, QueryType
from gs_quant.data import DataContext


def test_build_market_data_query():
    asset_ids = ['MA4B66MW5E27U8P3295']
    query_type = QueryType.IMPLIED_VOLATILITY
    where = {'tenor': '1y', 'strikeReference': 'delta', 'relativeStrike': 0.1}
    source = None
    real_time = False
    measure = "Curve"
    with DataContext(start=datetime.date(2013, 1, 1), end=datetime.date(2025, 2, 1)):
        queries = GsDataApi.build_market_data_query(asset_ids, query_type, where, source, real_time, measure,
                                                    parallel_pool_size=3)
        payload = {'entityIds': ['MA4B66MW5E27U8P3295'],
                   'queryType': 'Implied Volatility',
                   'where': {'tenor': '1y', 'strikeReference': 'delta', 'relativeStrike': 0.1},
                   'source': 'any',
                   'frequency': 'End Of Day',
                   'measures': ['Curve']}

        dates = [{'startDate': datetime.date(2013, 1, 1), 'endDate': datetime.date(2017, 1, 11)},
                 {'startDate': datetime.date(2017, 1, 11), 'endDate': datetime.date(2021, 1, 21)},
                 {'startDate': datetime.date(2021, 1, 21), 'endDate': datetime.date(2025, 1, 31)}]

        expected = [{'queries': [{**payload, **date_range}]} for date_range in dates]
        assert expected == queries

    with DataContext(start=datetime.date(2013, 1, 1), end=datetime.date(2025, 1, 1)):
        queries = GsDataApi.build_market_data_query(asset_ids, query_type, where, source, real_time, measure)
        payload = {'entityIds': ['MA4B66MW5E27U8P3295'],
                   'queryType': 'Implied Volatility',
                   'where': {'tenor': '1y', 'strikeReference': 'delta', 'relativeStrike': 0.1},
                   'source': 'any',
                   'frequency': 'End Of Day',
                   'measures': ['Curve'],
                   'startDate': datetime.date(2013, 1, 1),
                   'endDate': datetime.date(2025, 1, 1)}

        expected = {'queries': [payload]}
        assert expected == queries
