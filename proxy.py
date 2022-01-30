# Copyright (c) 2019-2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import requests
import threading
import uwsgi

def application(env: dict, start_response):

    # parse the request path
    request_path = str(env.get('PATH_INFO'))
    paths = request_path.split('/')
    if len(paths) > 1:
        del paths[0]

    if len(paths) < 2:
        return send_response({
            'code': 1004,
            'error': 'Bad request path ' + request_path
        }, start_response)
    elif len(paths) > 3:
        return send_response({
            'code': 1004,
            'error': 'Bad request path ' + request_path
        }, start_response)

    namesp = paths[0]
    api = paths[1]

    if not namesp or not api:
        return send_response({
            'code': 1004,
            'error': 'Bad request path ' + request_path
        }, start_response)

    try:
        response = call_api(namesp, api, env)
        return send_response(response, start_response)
    except ValueError as e:
        return send_response({
            'code': 1002,
            'error': 'Internal Server Error: failed to call ' + api
                     + ' : ' + getattr(e, 'message', repr(e))
        }, start_response)
    except:
        return send_response({
            'code': 1002,
            'error': 'Internal Server Error: failed to call ' + api
        }, start_response)


def call_api(namesp: str, api: str, env: dict):
    is_v1 = namesp == 'v1'

    try:
        request_body_size = int(env.get('CONTENT_LENGTH', 0))
    except ValueError:
        request_body_size = 0

    params = []
    if request_body_size > 0:
        request_body = env.get('wsgi.input').read(request_body_size)
        if request_body != b'\n':
            try:
                data = request_body.decode('utf8')
                params += json.loads(data)
            except:
                pass

    if is_v1:
        if 'URL_' + api + '_HOSTIP' in uwsgi.opt:
            return call_url(api, params, env)


def call_url(api: str, params: any, env: dict):
    rpchost = uwsgi.opt.get('URL_' + api + '_HOSTIP', b'').decode('utf8')
    rpcport = uwsgi.opt.get('URL_' + api + '_PORT', b'').decode('utf8')
    rpcurl = 'http://' + rpchost + ':' + rpcport + str(env.get('PATH_INFO', b''))

    headers = {
        'Content-Type': 'application/json'
    }
    payload = '' if len(params) == 0 else json.dumps(params)

    try:
        res = requests.post(rpcurl, headers=headers, data=payload)
        try:
            response = json.loads(res.content)
            return parse_result(response)
        except:
            return res.content.decode('utf8')
    except:
        return {
            'code': 1002,
            'error': 'Internal Server Error: failed to connect to ' + api
        }


def parse_result(res: any):
    if 'result' in res and res['result']:
        return res['result']
    else:
        return res


def send_response(result: any, start_response):
    headers = [('Content-Type', 'application/json')]
    res_data = result.encode('utf8') if isinstance(result, str) else json.dumps(result).encode('utf8')

    start_response('200 OK', headers)
    return res_data
