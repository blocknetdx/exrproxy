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

    try:
        host = os.environ.get('XQUERY_HOST', 'http://localhost:81')
        port = host.split(":")[-1]
        headers = {'content-type': 'application/json'}
        # results = []
        if path.count("/") <= 1:
            url = host+'/help'
            print(url)
            response = requests.get(url, timeout=15)
            text = response.text()
            text = text.replace(f"localhost:{port}"),f"127.0.0.1/xrs/xquery/{path.replace('/','')}"
            return Response(headers=response.headers, response=text)
        elif 'help' not in path:
            url = host + '/' + '/'.join(path.split('/')[1::])
            print(url)
            response = requests.get(url, timeout=15)
            return Response(headers=response.headers, response=response.json())
        else:
            url = host + '/' + '/'.join(path.split('/')[1::])
            print(url)
            response = requests.post(url, headers=headers, json=request.get_json(), timeout=15)
            return Response(headers=response.headers, response=response.json())
    except Exception as e:
        print(e)
        logging.debug(e)
        response = {
            'error': f"{e}",
            'message': "An error has occurred!",
            'error': 1000
        }
        return Response(headers=headers, response=json.dumps(response), status=400)


@app.route('/xrs/xquery', methods=['HEAD', 'GET'])
def xquery_root():
    return '''
<h1>xquery is supported on this host</h1>
    '''


