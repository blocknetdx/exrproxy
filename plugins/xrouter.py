# Copyright (c) 2019-2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging

import requests
import uwsgi
from flask import Blueprint, g, request
from requests.auth import HTTPDigestAuth

import exr

app = Blueprint('xrouter', __name__)


@app.route('/xr/<token>/<method>')
@exr.dec_check_token_method
@exr.dec_handle_payment
def xr(token, method):
    logging.debug('xr handle request: %s %s', token, method)
    return handle_request(request, exr.XR)


@app.route('/xrs/<service>')
@exr.dec_check_token_method
@exr.dec_handle_payment
def xrs(service):
    logging.debug('xrs handle request: %s', service)
    return handle_request(request, exr.XRS)


def handle_request(req, namesp):
    token = g.token
    xrfunc = g.xrfunc

    try:
        response = call_xrfunc(namesp, token, xrfunc, req.environ)
        return exr.send_response(response, exr.config.get_snodekey())
    except ValueError as e:
        return exr.send_response({
            'code': 1002,
            'error': 'Internal Server Error: failed to call method ' + xrfunc + ' for token ' + token
                     + ' : ' + getattr(e, 'message', repr(e))
        }, exr.config.get_snodekey())
    except:
        return exr.send_response({
            'code': 1002,
            'error': 'Internal Server Error: failed to call method ' + xrfunc + ' for token ' + token
        }, exr.config.get_snodekey())


def call_xrfunc(namesp: str, token: str, xrfunc: str, env: dict):
    logging.debug('call_xrfunc_namesp: {} token: {} xrfunc: {} env: {}'.format(namesp, token, xrfunc, env))
    is_xrouter_plugin = namesp == exr.XRS

    # obtain host info
    rpchost = uwsgi.opt.get('RPC_' + token + '_HOSTIP', b'').decode('utf8')
    rpcport = uwsgi.opt.get('RPC_' + token + '_PORT', b'').decode('utf8')
    rpcuser = uwsgi.opt.get('RPC_' + token + '_USER', b'').decode('utf8')
    rpcpass = uwsgi.opt.get('RPC_' + token + '_PASS', b'').decode('utf8')
    rpcver = uwsgi.opt.get('RPC_' + token + '_VER', b'1.0').decode('utf8')
    rpcmethod = ''

    try:
        request_body_size = int(env.get('CONTENT_LENGTH', 0))
    except ValueError:
        request_body_size = 0

    params = []
    logging.debug('checking request_body_size')
    if request_body_size > 0:
        request_body = env.get('wsgi.input').read(request_body_size)
        if request_body != b'\n':
            try:
                data = request_body.decode('utf8')
                logging.debug('request_body_data: {}'.format(data))
                params = json.loads(data)
                logging.debug('params: {}'.format(params))
            except:
                pass

    if is_xrouter_plugin:
        logging.debug('is_xrouter_plugin: {}'.format(is_xrouter_plugin))
        if 'RPC_' + token + '_METHOD' in uwsgi.opt:
            logging.debug('rpcmethod set')
            rpcmethod = uwsgi.opt.get('RPC_' + token + '_METHOD', b'').decode('utf8')
        elif 'URL_' + token + '_HOSTIP' in uwsgi.opt:
            logging.debug('CALL_URL_is_xr_plugin_xrfunc: {} params: {} env: {}'.format(xrfunc, params, env))
            return call_url(xrfunc, params, env)

    if not rpchost or not rpcport or not rpcuser or not rpcpass or (is_xrouter_plugin and not rpcmethod):
        return {
            'code': 1002,
            'error': 'Internal Server Error: bad proxy configuration for token ' + token
        }

    # resolve the rpc name from the supplied xrouter call
    rpc_method = rpcmethod.lower() if is_xrouter_plugin else xr_to_rpc(token, xrfunc)
    if not rpc_method:
        return {
            'code': 1031,
            'error': 'Unsupported call ' + xrfunc + ' for token ' + token
        }

    rpcurl = 'http://' + rpcuser + ':' + rpcpass + '@' + rpchost + ':' + rpcport
    if rpcuser == '' and rpcpass == '':  # if no rpc credentials
        rpcurl = 'http://' + rpchost + ':' + rpcport
    headers = {'Content-Type': 'application/json'}

    l_xr_method = xrfunc.lower()
    l_token = token.lower()

    if l_token == 'eth' or l_token == 'etc':
        if l_xr_method == 'xrdecoderawtransaction':
            pass
        if l_xr_method == 'xrgetblockcount':
            payload = json.dumps({
                'id': 1,
                'method': rpc_method,
                'params': params,
                'jsonrpc': rpcver
            })

            try:        
                res = requests.post(rpcurl, headers=headers, data=payload)
                try:
                    response = parse_result(json.loads(res.content))
                    count = int(response, 16)
                    return count
                except ValueError:
                    return res.content.decode('utf8')  # return raw string if json decode fails
            except:
                return {
                    'code': 1002,
                    'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                }
        if l_xr_method == 'xrgetblockhash':
            if isinstance(params[0], int):
                params = [hex(params[0]), False]
            elif isinstance(params[0], str) and not params[0].startswith('0x'):
                try:  # first check if int
                    i = int(params[0])
                    params = [hex(i), False]
                except ValueError:
                    params = ['0x' + params[0], False]
            else:
                params = [params[0], False]

            payload = json.dumps({
                'id': 1,
                'method': rpc_method,
                'params': params,
                'jsonrpc': rpcver
            })

            try:        
                res = requests.post(rpcurl, headers=headers, data=payload)
                try:
                    response = json.loads(res.content)
                    block_hash = str(response['result']['hash'])
                    return block_hash
                except ValueError:
                    return res.content.decode('utf8')  # return raw string if json decode fails
            except:
                return {
                    'code': 1002,
                    'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                }
        if l_xr_method == 'xrgetblock':
            params = [params[0], False]
        if l_xr_method == 'xrgetblocks' or l_xr_method == 'xrgettransactions':  # iterate over all ids
            response = []
            for b_id in params:
                parsed_id: any
                rpc_method2 = rpc_method
                if isinstance(b_id, int):
                    parsed_id = hex(b_id)
                    if l_xr_method == 'xrgetblocks':
                        rpc_method2 = 'eth_getBlockByNumber'
                else:
                    parsed_id = b_id
                params2 = [parsed_id, False]
                if l_xr_method == 'xrgettransactions':
                    params2 = [parsed_id] # transactions doesn't support 2nd parameter
                payload = json.dumps({
                    'id': 1,
                    'method': rpc_method2,
                    'params': params2,
                    'jsonrpc': rpcver
                })
                try:
                    res = requests.post(rpcurl, headers=headers, data=payload)
                    response += [parse_result(json.loads(res.content))]
                except:
                    return {
                        'code': 1002,
                        'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                    }
            return response
        if l_xr_method == 'xrgettransaction':
            pass
        if l_xr_method == 'xrsendtransaction':
            pass
    elif l_token == 'neo':
        if l_xr_method == 'xrdecoderawtransaction':
            pass
        if l_xr_method == 'xrgetblockcount':
            pass
        if l_xr_method == 'xrgetblockhash':
            params[0] = int(params[0])
        if l_xr_method == 'xrgetblock':
            params = [params[0], 1]
        if l_xr_method == 'xrgetblocks' or l_xr_method == 'xrgettransactions': # iterate over all ids
            response = []
            for b_id in params:
                params2 = [b_id]
                if l_xr_method == 'xrgettransactions' or l_xr_method == 'xrgetblocks':
                    params2 += [1]
                payload = json.dumps({
                    'id': 1,
                    'method': rpc_method,
                    'params': params2,
                    'jsonrpc': rpcver
                })
                try:
                    res = requests.post(rpcurl, headers=headers, data=payload)
                    response += [parse_result(json.loads(res.content))]
                except:
                    return {
                        'code': 1002,
                        'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                    }
            return response
        if l_xr_method == 'xrgettransaction':
            params = [params[0], 1]
        if l_xr_method == 'xrsendtransaction':
            pass    
    elif l_token == 'xmr':
        rpcurl = 'http://' + rpchost + ':' + rpcport + '/json_rpc'
        auth = HTTPDigestAuth(rpcuser,rpcpass)
        payload = json.dumps({
            'id': 1,
            'method': rpc_method,
            'params': params,
            'jsonrpc': rpcver
        })

        if l_xr_method == 'xrdecoderawtransaction':
            pass
        if l_xr_method == 'xrgetblockcount':
            try:                
                res = requests.post(rpcurl, headers=headers, data=payload, auth=auth)
                try:
                    response = json.loads(res.content)
                    count = str(response['result']['count'])
                    return count
                except ValueError:
                    return res.content.decode('utf8')  # return raw string if json decode fails
            except:
                return {
                    'code': 1002,
                    'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                }
        if l_xr_method == 'xrgetblockhash':
            params[0] = int(params[0])
        if l_xr_method == 'xrgetblock':
            payload = json.dumps({
                'id': 1,
                'method': rpc_method,
                'params': {'hash':params[0]},
                'jsonrpc': rpcver
            })
        if l_xr_method == 'xrgetblocks': # iterate over all ids
            response = []
            for b_id in params:
                params2 = b_id
                if l_xr_method == 'xrgetblocks':
                    payload = json.dumps({
                        'id': 1,
                        'method': rpc_method,
                        'params': {'hash':params2},
                        'jsonrpc': rpcver
                    })
                try:
                    res = requests.post(rpcurl, headers=headers, data=payload, auth=auth)
                    response += [parse_result(json.loads(res.content))]
                except:
                    return {
                        'code': 1002,
                        'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                    }
            return response
        if l_xr_method == 'xrgettransaction':
            rpcurl = 'http://' + rpchost + ':' + rpcport + '/get_transactions'
            payload = json.dumps({
                'txs_hashes': [params[0]],
                'decode_as_json': True
            })
        if l_xr_method == 'xrgettransactions': # iterate over all ids
            rpcurl = 'http://' + rpchost + ':' + rpcport + '/get_transactions'
            response = []
            for b_id in params:
                params2 = b_id
                if l_xr_method == 'xrgettransactions':
                    payload = json.dumps({
                        'txs_hashes': [params2],
                        'decode_as_json': True
                    })
                try:
                    res = requests.post(rpcurl, headers=headers, data=payload, auth=auth)
                    response += [parse_result(json.loads(res.content))]
                except:
                    return {
                        'code': 1002,
                        'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                    }
            return response
        if l_xr_method == 'xrsendtransaction':
            rpcurl = 'http://' + rpchost + ':' + rpcport + '/send_raw_transaction'
            payload = json.dumps({
                'tx_as_hex': params[0],
                'do_not_relay': False
            })

        try:            
            res = requests.post(rpcurl, headers=headers, data=payload, auth=auth)
            try:
                response = parse_result(json.loads(res.content))
                return response
            except ValueError:
                return res.content.decode('utf8')  # return raw string if json decode fails
        except:
            return {
                'code': 1002,
                'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
            }
    else:
        if l_xr_method == 'xrdecoderawtransaction':
            pass
        if l_xr_method == 'xrgetblockcount':
            pass
        if l_xr_method == 'xrgetblockhash':
            params[0] = int(params[0])
        if l_xr_method == 'xrgetblock':
            pass
        if l_xr_method == 'xrgetblocks' or l_xr_method == 'xrgettransactions': # iterate over all ids
            response = []
            for b_id in params:
                params2 = [b_id]
                if l_xr_method == 'xrgettransactions':
                    params2 += [1]
                payload = json.dumps({
                    'id': 1,
                    'method': rpc_method,
                    'params': params2,
                    'jsonrpc': rpcver
                })
                try:
                    res = requests.post(rpcurl, headers=headers, data=payload)
                    response += [parse_result(json.loads(res.content))]
                except:
                    return {
                        'code': 1002,
                        'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
                    }
            return response
        if l_xr_method == 'xrgettransaction':
            params = [params[0], 1]
        if l_xr_method == 'xrsendtransaction':
            pass

    payload = json.dumps({
        'id': 1,
        'method': rpc_method,
        'params': params,
        'jsonrpc': rpcver
    })

    try:        
        res = requests.post(rpcurl, headers=headers, data=payload)
        try:
            response = parse_result(json.loads(res.content))
            return response
        except ValueError:
            return res.content.decode('utf8')  # return raw string if json decode fails
    except:
        return {
            'code': 1002,
            'error': 'Internal Server Error: failed to connect to ' + xrfunc + ' for token ' + token
        }


def call_url(xrfunc: str, params: any, env: dict):
    logging.debug('### call_url_params: {}'.format(params))
    rpchost = uwsgi.opt.get('URL_' + xrfunc + '_HOSTIP', b'').decode('utf8')
    rpcport = uwsgi.opt.get('URL_' + xrfunc + '_PORT', b'').decode('utf8')
    rpcurl = 'http://' + rpchost + ':' + rpcport + str(env.get('PATH_INFO', b''))

    headers = {
        'Content-Type': 'application/json',
        'XR-Pubkey': str(env.get('HTTP_XR_PUBKEY', b'')),
        'XR-Signature': str(env.get('HTTP_XR_SIGNATURE', b'')),
        'XR-Payment': str(env.get('HTTP_XR_PAYMENT', b'')),
    }
    payload = '' if len(params) == 0 else json.dumps(params)

    try:
        logging.debug('call_url payload: {} headers: {} rpcurl: {}'.format(payload,headers,rpcurl))
        res = requests.post(rpcurl, headers=headers, data=payload)
        try:
            logging.debug('call_url_post_response: {}'.format(res.text))
            response = res.text
            return response
        except:
            return res.content.decode('utf8')
    except:
        return {
            'code': 1002,
            'error': 'Internal Server Error: failed to connect to ' + xrfunc
        }


def parse_result(res: any):
    if 'result' in res and res['result']:
        return res['result']
    else:
        return res


def xr_to_rpc(token: str, xr_func: str):
    l_xr_method = xr_func.lower()
    l_token = token.lower()

    if l_token == 'eth' or l_token == 'etc':
        if l_xr_method == 'xrdecoderawtransaction': return ''
        if l_xr_method == 'xrgetblockcount': return 'eth_blockNumber'
        if l_xr_method == 'xrgetblockhash': return 'eth_getBlockByNumber'
        if l_xr_method == 'xrgetblock': return 'eth_getBlockByHash'
        if l_xr_method == 'xrgetblocks': return 'eth_getBlockByHash'
        if l_xr_method == 'xrgettransaction': return 'eth_getTransactionByHash'
        if l_xr_method == 'xrgettransactions': return 'eth_getTransactionByHash'
        if l_xr_method == 'xrsendtransaction': return 'eth_sendRawTransaction'
    elif l_token == 'neo':
        if l_xr_method == 'xrdecoderawtransaction': return ''
        if l_xr_method == 'xrgetblockcount': return 'getblockcount'
        if l_xr_method == 'xrgetblockhash': return 'getblockhash'
        if l_xr_method == 'xrgetblock': return 'getblock'
        if l_xr_method == 'xrgetblocks': return 'getblock'
        if l_xr_method == 'xrgettransaction': return 'getrawtransaction'
        if l_xr_method == 'xrgettransactions': return 'getrawtransaction'
        if l_xr_method == 'xrsendtransaction': return 'sendrawtransaction'        
    elif l_token == 'xmr':
        if l_xr_method == 'xrdecoderawtransaction': return ''
        if l_xr_method == 'xrgetblockcount': return 'get_block_count'
        if l_xr_method == 'xrgetblockhash': return 'on_get_block_hash'
        if l_xr_method == 'xrgetblock': return 'get_block'
        if l_xr_method == 'xrgetblocks': return 'get_block'
        if l_xr_method == 'xrgettransaction': return 'get_transactions'
        if l_xr_method == 'xrgettransactions': return 'get_transactions'
        if l_xr_method == 'xrsendtransaction': return 'send_raw_transaction'
    else:
        if l_xr_method == 'xrdecoderawtransaction': return 'decoderawtransaction'
        if l_xr_method == 'xrgetblockcount': return 'getblockcount'
        if l_xr_method == 'xrgetblockhash': return 'getblockhash'
        if l_xr_method == 'xrgetblock': return 'getblock'
        if l_xr_method == 'xrgetblocks': return 'getblock'
        if l_xr_method == 'xrgettransaction': return 'getrawtransaction'
        if l_xr_method == 'xrgettransactions': return 'getrawtransaction'
        if l_xr_method == 'xrsendtransaction': return 'sendrawtransaction'

    return ''

