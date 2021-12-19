# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os

import requests
from flask import Blueprint, Response, g, jsonify, request
from plugins.xquery.middleware import authenticate
# from plugins.xquery import util

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


@app.route('/xrs/xquery/<project_id>/<path:path>', methods=['POST'])
@authenticate
def handle_request(project_id, path):

    try:
        host = os.environ.get('XQUERY_HOST', 'http://localhost:81')
        port = host.split(":")[-1]
        headers = {'content-type': 'application/json'}
        if path in ['help','help/']:
            url = host+'/help'
            response = requests.get(url, timeout=15)
            text = response.text
            text = text.replace(f"localhost:{port}",f"127.0.0.1/xrs/xquery/{project_id}")
            return Response(headers=response.headers.items(), response=text)
        elif 'help' not in path:
            url = host + '/' + path
            response = requests.post(url, headers=headers, json=request.get_json(), timeout=15)
            resp = json.dumps(response.json())
            header = response.headers
            header['Content-Type']='application/json'
            header['Content-Length']=len(resp)
            header['Keep-Alive']='timeout=15, max=100'
            header['Content-Encoding']='UTF-8'
            return Response(headers=header.items(), response=resp)
        else:
            url = host + '/' + path
            response = requests.get(url, timeout=15)
            if 'help/graph' in path:
                resp = json.dumps(response.json())
                header = response.headers
                header['Content-Type']='application/json'
                header['Content-Length']=len(resp)
                header['Keep-Alive']='timeout=15, max=100'
                return Response(headers=header.items(), response=resp)
            else:
                resp = response.text
                return Response(headers=headers.items(), response=resp)
    except Exception as e:
        logging.debug(e)
        response = {
            'exception': f'{e}',
            'message': "An error has occurred!",
            'error': 1000
        }
        return Response(headers=headers, response=json.dumps(response), status=400)


@app.route('/xrs/xquery', methods=['HEAD', 'GET'])
def xquery_root():
    return '''
<h1>xquery is supported on this host</h1>
    '''


