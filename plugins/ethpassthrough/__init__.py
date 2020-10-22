# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os

from flask import Blueprint, Response, g, jsonify, request

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

    data = request.get_json()

    try:
        method = data['method']
        params = data['params']
        logging.debug('Received Method: {}, Params: {}'.format(method, params))

        response = req_handler.post_eth_proxy(method=method, params=params)
        if type(response) == list:
            response = response[0]

        return Response(headers=headers, response=json.dumps(response))
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
    json_data = request.get_json(force=True)
    if 'method' in json_data and json_data['method'] == 'request_project':
        project = req_handler.get_project()
        logging.info('Project Requested: {}'.format(project))
        return jsonify(project)

    return eth_passthough_root()
