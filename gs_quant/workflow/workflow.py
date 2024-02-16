"""
Copyright 2023 Goldman Sachs.
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
from typing import Optional, Tuple

from dataclasses_json import global_config

from gs_quant.json_convertors import decode_hedge_type, decode_hedge_types
from gs_quant.target.workflow_quote import HedgeTypes

global_config.decoders[Optional[HedgeTypes]] = decode_hedge_type
global_config.decoders[HedgeTypes] = decode_hedge_type
global_config.decoders[Optional[Tuple[HedgeTypes, ...]]] = decode_hedge_types
