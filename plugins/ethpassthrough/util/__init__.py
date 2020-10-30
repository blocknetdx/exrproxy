# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import json


def make_jsonrpc_data(data: any):
    """Parse json post data into required json-rpc object. This call also supports parsing
    XRouter posted data into json-rpc. XRouter posts data as a json list, e.g. [param1, param2, etc...]"""
    method = ''
    params = []

    # handle xrouter data
    if isinstance(data, list):
        if not data or len(data) < 2:  # if no data, we don't have enough info to process (missing method and project)
            return None
        # project_id = data[0]
        method = data[1]
        p = [] if len(data) <= 2 else data[2] if not isinstance(data[2], str) else str.strip(data[2])
        if p == '':
            p = []
        try:
            params = json.loads(p) if isinstance(p, str) and (str.startswith(p, '[') or str.startswith(p, '{')) else p
            if isinstance(params, str) or isinstance(params, dict):
                params = [params]
        except:
            return None

    # check if this is already a json-rpc obj
    if 'jsonrpc' in data and 'method' in data and 'params' in data and 'id' in data:
        return data

    if 'method' in data and 'params' in data:
        method = data['method']
        params = data['params']

    if not method:
        return None

    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": "exr"
    }
