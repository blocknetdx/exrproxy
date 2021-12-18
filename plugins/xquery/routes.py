# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os

import requests
from flask import Blueprint, Response, g, jsonify, request

from plugins.xquery import util

app = Blueprint('xquery', __name__)


@app.errorhandler(400)
def bad_request_error(error):
    response = jsonify({
        'error': 'Bad Request ' + error
    })
    return response


@app.errorhandler(500)
def internal_server_error(error):
    response = jsonify({
        'error': 'Internal Server Error'
    })
    return response


@app.errorhandler(401)
def unauthorized_error(error):
    response = jsonify({
        'error': 'Unauthorized User Access'
    })
    return response


@app.route('/xrs/xquery/<path:path>', methods=['POST'])
def handle_request(path):

    data = []
    batch = False
    try:
        req_data = request.get_json()
        if not req_data:
            return bad_request_error('missing parameters')

        # Check if xrouter call (this only has a single request)
        if util.is_xrouter_call(req_data):
            data.append(util.make_jsonrpc_data(req_data))
        else:  # Look for multiple requests (list of jsonrpc calls)
            if isinstance(req_data, list):
                batch = True
                for r in req_data:
                    data.append(util.make_jsonrpc_data(r))
            else:
                data.append(util.make_jsonrpc_data(req_data))
        if not data:
            raise ValueError('failed to parse json data')

        # Check each json rpc call
        for d in data:
            method = d['method']
            params = d['params']
            logging.debug('Received Method: {}, Params: {}'.format(method, params))

    except Exception as e:
        logging.debug(e)
        return Response(response=json.dumps({
            'message': "malformed json post data",
            'error': 1000
        }))

    try:
        host = os.environ.get('XQUERY_HOST', 'http://localhost:81')
        port = host.split(":")[-1]
        headers = {'content-type': 'application/json'}
        results = []
        if path.count("/") <= 1:
            response = requests.get(host+'/help', timeout=15)
            results.append(response.text().replace(f"localhost:{port}"),f"127.0.0.1/xrs/xquery/{path.replace('/','')}")
        else:
            for d in data:
                response = requests.post(host + '/' + '/'.join(path.split('/')[1::]), headers=headers, data=json.dumps(d), timeout=15)
                results.append(response.json())
            # If batch request return list
        return Response(headers=headers, response=json.dumps(results if batch or len(results) > 1 else results[0]))
    except Exception as e:
        logging.debug(e)
        response = {
            'message': "An error has occurred!",
            'error': 1000
        }
        return Response(headers=headers, response=json.dumps(response), status=400)


@app.route('/xrs/xquery', methods=['HEAD', 'GET'])
def xquery_root():
    return '''
<h1>xquery is supported on this host</h1>
    '''


