# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os
import threading

import requests
from flask import Blueprint, Response, g, jsonify, request
from requests.auth import HTTPDigestAuth

from plugins.eth_passthrough import util
from plugins.projects.database.models import db_session, select, Project
from plugins.projects.middleware import authenticate
from plugins.eth_passthrough.util.request_handler import RequestHandler

app = Blueprint('eth_passthrough', __name__)
req_handler = RequestHandler()


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


@app.route('/xrs/eth_passthrough/<project_id>', methods=['POST'])
@authenticate
def handle_request(project_id):
    headers = {
        'PROJECT-ID': project_id,
        'API-TOKENS': g.project.api_token_count,
        'API-TOKENS-USED': g.project.used_api_tokens,
        'API-TOKENS-REMAINING': g.project.api_token_count - g.project.used_api_tokens
    }

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

            env_disallowed_methods = os.environ.get('ETH_HOST_DISALLOWED_METHODS',
                                                    'eth_accounts,db_putString,db_getString,db_putHex,db_getHex')
            if method in set(env_disallowed_methods.split(',')):
                return unauthorized_error(f'disallowed method {method}')
    except Exception as e:
        logging.debug(e)
        return Response(headers=headers, response=json.dumps({
            'message': "malformed json post data",
            'error': 1000
        }))

    try:
        host = os.environ.get('ETH_HOST', 'http://localhost:8545')
        eth_user = os.environ.get('ETH_HOST_USER', '')
        eth_pass = os.environ.get('ETH_HOST_PASS', '')
        headers = {'content-type': 'application/json'}
        results = []
        # Make multiple requests to geth endpoint and store results
        if eth_user:  # only set auth params if defined
            auth = HTTPDigestAuth(eth_user, eth_pass)
            for d in data:
                response = requests.post(host, headers=headers, data=json.dumps(d), auth=auth, timeout=15)
                results.append(response.json())
        else:
            for d in data:
                response = requests.post(host, headers=headers, data=json.dumps(d), timeout=15)
                results.append(response.json())

        # Update api count in background
        update_api_thread = threading.Thread(target=update_api_count, name="update_api_count", args=[project_id])
        update_api_thread.start()

        # If batch request return list
        return Response(headers=headers, response=json.dumps(results if batch or len(results) > 1 else results[0]))
    except Exception as e:
        logging.debug(e)
        response = {
            'message': "An error has occurred!",
            'error': 1000
        }
        return Response(headers=headers, response=json.dumps(response), status=400)


@app.route('/xrs/eth_passthrough', methods=['HEAD', 'GET'])
def eth_passthough_root():
    return '''
<h1>eth_passthrough is supported on this host</h1>
    '''


@app.route('/xrs/eth_passthrough', methods=['POST'])
def xrouter_call():
    try:
        json_data = request.get_json(force=True)
    except Exception as e:
        logging.debug(e)
        return bad_request_error('malformed json post data')

    # Support XRouter calls to eth_passthrough. XRouter posts an array of parameters.
    # The expected format for eth_passthrough is:
    # [string, string, string_json_array]
    # ["project_id", "method", "[parameters...]"]
    if isinstance(json_data, list) and len(json_data) >= 3:
        project_id = json_data[0]
        if project_id is None or project_id is '':
            return bad_request_error('Invalid project id')
        data = util.make_jsonrpc_data(json_data)
        if not data:
            return bad_request_error('invalid post data')
        # Check xrouter requests for api key
        api_key = util.get_api_key(json_data)
        return req_handler.post_eth_proxy_project(request.host, data, project_id, api_key)

    return eth_passthough_root()


def update_api_count(project_id):
    res = req_handler.post_update_api_count(project_id)
    logging.debug('update_api_count {} {}'.format(project_id, res))

