# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import unittest

from plugins.ethpassthrough.util import make_jsonrpc_data


class TestJsonParams(unittest.TestCase):
    def test_make_jsonrpc_data_xrouter(self):
        data = ["my-project-id", "eth_blockNumber", "[]"]
        result = make_jsonrpc_data(data)
        expected = {
            "jsonrpc": "2.0",
            "method": data[1],
            "params": json.loads(data[2]),
            "id": "exr"
        }
        self.assertEqual(json.dumps(result), json.dumps(expected), 'empty parameter list should be ok')

        data = ['my-project-id', 'eth_blockNumber', '']
        result = make_jsonrpc_data(data)
        expected = {
            "jsonrpc": "2.0",
            "method": data[1],
            "params": [],
            "id": "exr"
        }
        self.assertEqual(json.dumps(result), json.dumps(expected), 'missing parameter list should be ok')

        data = ["my-project-id", "eth_blockNumber"]
        result = make_jsonrpc_data(data)
        expected = {
            "jsonrpc": "2.0",
            "method": data[1],
            "params": [],
            "id": "exr"
        }
        self.assertEqual(json.dumps(result), json.dumps(expected), 'missing parameters should default to empty')

        data = ["my-project-id", "eth_blockNumber", "{\"one\": 1}"]
        result = make_jsonrpc_data(data)
        expected = {
            "jsonrpc": "2.0",
            "method": data[1],
            "params": [{"one": 1}],
            "id": "exr"
        }
        self.assertEqual(json.dumps(result), json.dumps(expected), 'should support json object as parameter')

        data = ["my-project-id", "eth_blockNumber", "one"]
        result = make_jsonrpc_data(data)
        expected = {
            "jsonrpc": "2.0",
            "method": data[1],
            "params": ["one"],
            "id": "exr"
        }
        self.assertEqual(json.dumps(result), json.dumps(expected), 'should support raw string parameter')

        data = ["my-project-id", "eth_blockNumber", "{this is not valid json}"]
        result = make_jsonrpc_data(data)
        self.assertEqual(result, None, 'bad json in parameter should fail')

        data = ["my-project-id"]
        result = make_jsonrpc_data(data)
        self.assertEqual(result, None, 'missing method should fail')

        data = []
        result = make_jsonrpc_data(data)
        self.assertEqual(result, None, 'empty data should fail')


if __name__ == '__main__':
    unittest.main()
