# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os
import threading
import uwsgi
import requests
from flask import Blueprint, Response, g, jsonify, request
from plugins.projects.middleware import authenticate
from plugins.projects.util.request_handler import RequestHandler
from plugins import limiter

app = Blueprint('xquery', __name__)
limiter.limit("50/minute;3000/hour;72000/day")(app)
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


@app.route('/xrs/xquery/<project_id>/', methods=['POST'], strict_slashes=False)
@app.route('/xrs/xquery/<project_id>/<path:path>', methods=['POST'], strict_slashes=False)
@authenticate
def handle_request(project_id, path=None):
    project_headers = {
        'PROJECT-ID': project_id,
        'API-TOKENS': str(g.project.api_token_count),
        'API-TOKENS-USED': str(g.project.used_api_tokens),
        'API-TOKENS-REMAINING': str(g.project.api_token_count - g.project.used_api_tokens)
    }
    try:
        host_ip = uwsgi.opt.get('XQUERY_IP', b'localhost').decode('utf8')
        host_port = uwsgi.opt.get('XQUERY_PORT', b'81').decode('utf8')
        host = 'http://'+host_ip+':'+host_port
        headers = {'content-type': 'application/json'}
        if path in ['help','help/'] or path==None:
            url = host+'/help'
            response = requests.get(url, timeout=300)
            text = response.text
            text = text.replace(f"localhost:{host_port}",f"127.0.0.1/xrs/xquery/{project_id}")
            return Response(headers={**response.headers,**project_headers}.items(), response=text)
        elif 'help' not in path:
            url = host + '/' + path
            response = requests.post(url, headers=headers, json=request.get_json(), timeout=300)
            resp = json.dumps(response.json())
            header = response.headers
            header['Content-Type']='application/json'
            header['Content-Length']=len(resp)
            header['Keep-Alive']='timeout=15, max=100'
            header['Content-Encoding']='UTF-8'
            update_in_background_api_count(project_id)
            return Response(headers={**header,**project_headers}.items(), response=resp)
        else:
            url = host + '/' + path
            response = requests.get(url, timeout=300)
            if 'help/graph' in path:
                resp = json.dumps(response.json())
                header = response.headers
                header['Content-Type']='application/json'
                header['Content-Length']=len(resp)
                header['Keep-Alive']='timeout=15, max=100'
                return Response(headers={**header,**project_headers}.items(), response=resp)
            else:
                resp = response.text
                return Response(headers={**headers,**project_headers}.items(), response=resp)
    except Exception as e:
        logging.critical('Exception: ',exc_info=True)
        response = {
            'message': "An error has occurred!",
            'error': 1000
        }
        return Response(headers={**headers,**project_headers}.items(), response=json.dumps(response), status=400)


@app.route('/xrs/xquery', methods=['HEAD', 'GET'])
def xquery_root():
    return '''
<h1>xquery is supported on this host</h1>
    '''


def update_in_background_api_count(project_id):
    update_api_thread = threading.Thread(target=update_api_count, name="update_api_count", args=[project_id])
    update_api_thread.start()

def update_api_count(project_id):
    res = req_handler.post_update_api_count(project_id)
    logging.debug('update_api_count {} {}'.format(project_id, res))

