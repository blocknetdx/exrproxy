# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os

import requests
from flask import Blueprint, Response, g, jsonify, request
from requests.auth import HTTPDigestAuth

from plugins.ethpassthrough import util
from plugins.ethpassthrough.database.models import db_session, select, Project
from plugins.ethpassthrough.util.middleware import authenticate
from plugins.ethpassthrough.util.request_handler import RequestHandler

app = Blueprint('eth_passthrough', __name__)
req_handler = RequestHandler()


@app.errorhandler(400)
def bad_request_error(error):
    response = jsonify({
        'error': 'Bad Request'
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


@app.route('/all_projects', methods=['GET'])
def all_projects():
    if not os.environ.get('DEBUG', False):
        return Response({}, 401)

    results = []
    try:
        with db_session:
            query = select(p for p in Project)

            results = [{
                'name': p.name,
                # 'api_key': p.api_key,
                'api_token_count': p.api_token_count,
                'used_api_tokens': p.used_api_tokens,
                'expires': str(p.expires),
                'active': p.active,
            } for p in query]
    except Exception as e:
        logging.error(e)

    return jsonify(results)


@app.route('/xrs/eth_passthrough/<project_id>', methods=['POST'])
@authenticate
def handle_request(project_id):
    headers = {
        'PROJECT-ID': project_id,
        'API-TOKENS': g.project.api_token_count,
        'API-TOKENS-USED': g.project.used_api_tokens,
        'API-TOKENS-REMAINING': g.project.api_token_count - g.project.used_api_tokens
    }

    try:
        data = util.make_jsonrpc_data(request.get_json())
        if not data:
            raise ValueError('failed to parse json data')
        method = data['method']
        params = data['params']
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
        if eth_user:  # only set auth params if defined
            auth = HTTPDigestAuth(eth_user, eth_pass)
            response = requests.post(host, headers=headers, data=json.dumps(data), auth=auth, timeout=15)
        else:
            response = requests.post(host, headers=headers, data=json.dumps(data), timeout=15)

        return Response(headers=headers, response=json.dumps(response.json()))
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
<div>
  To get started create a project:
  curl -X POST -d \'{"id": curltest, "method": "request_project", "params": TBD}\' http://host:port/xrs/eth_passthrough 
</div>
    '''


@app.route('/xrs/eth_passthrough', methods=['POST'])
def request_project():
    try:
        json_data = request.get_json(force=True)
    except Exception as e:
        logging.debug(e)
        return bad_request_error('malformed json post data')

    if 'method' in json_data and json_data['method'] == 'request_project':
        project = req_handler.get_project()
        logging.info('Project Requested: {}'.format(project))
        return jsonify(project)

    # Support XRouter calls to eth_passthrough. XRouter posts an array of parameters.
    # The expected format for eth_passthrough is:
    # [string, string, string_json_array]
    # ["project_id", "method", "[parameters...]"]
    if isinstance(json_data, list) and len(json_data) == 3:
        project_id = json_data[0]
        if project_id is None or project_id is '':
            return bad_request_error('Invalid project id')
        data = util.make_jsonrpc_data(json_data)
        if not data:
            return bad_request_error('invalid post data')
        return req_handler.post_eth_proxy_project(request.host, data, project_id)

    return eth_passthough_root()

