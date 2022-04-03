# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import json
import logging
import threading
from functools import wraps

import requests
import uwsgi
from flask import g, request, Response

import bitcoin.core
import bitcoin.signmessage
import bitcoin.wallet
from exr import config

XR = 'xr'
XRS = 'xrs'


def add_servicenode_signature(res_data, headers, snodekey: bitcoin.wallet.CKey):
    """Adds the service node signature to the headers. Signing is skipped if signing
    fails or the key is invalid. Signature added to header 'XR-Signature' and the
    public key associated with the signature is added to header 'XR-Pubkey'."""
    try:
        res_hash = bitcoin.core.Hash(bitcoin.core.serialize.BytesSerializer.serialize(res_data))
        sig, i = snodekey.sign_compact(res_hash)
        meta = 27 + i
        if snodekey.is_compressed:
            meta += 4
        headers['XR-Pubkey'] = snodekey.pub.hex()
        headers['XR-Signature'] = bitcoin.core.b2x(bitcoin.signmessage._bchr(meta) + sig)
    except Exception as e:
        logging.error('Unknown signing error: {}', getattr(e, 'message', repr(e)))
    return headers


def send_response(result: any, snodekey: bitcoin.wallet.CBitcoinSecret):
    """Sends a signed response to the client."""
    res_data = result.encode('utf8') if isinstance(result, str) else json.dumps(result).encode('utf8')
    headers = {}
    if snodekey:
        headers = add_servicenode_signature(res_data, {'Content-Type': 'application/json'}, snodekey)
    return Response(headers=headers, response=res_data)


def dec_check_token_method(f):
    """Decorator that checks for valid token, service, and method names.
    The values are added to the application context, e.g. g.token,
    g.service, and g.xrfunc"""
    @wraps(f)
    def wrap(*args, **kwargs):
        token = kwargs['token'] if 'token' in kwargs else ''
        service = kwargs['service'] if 'service' in kwargs else ''
        method = kwargs['method'] if 'method' in kwargs else ''

        if not token and not service:
            return send_response({
                'code': 1004,
                'error': 'Bad request path ' + request.path + ' , The path must be in the format '
                                                              '/xr/BLOCK/xrGetBlockCount'
            }, config.get_snodekey())

        xrpath = request.path.split('/')
        namesp = xrpath[1]

        xrfunc = ''
        if namesp == XR:
            xrfunc = method
        elif namesp == XRS:
            xrfunc = service

        logging.debug('token: {}'.format(token))

        if not xrfunc or (namesp == XR and not token):
            return send_response({
                'code': 1004,
                'error': 'Bad request path ' + request.path + ' , The path must have a namespace, a method, '
                                                              'and a token, for example: /xr/BLOCK/xrGetBlockCount'
            }, config.get_snodekey())

        # if xrouter plugin, set token to xr func name
        if namesp == XRS:
            token = xrfunc
            logging.debug('xrs token set value from xrfunc: {}'.format(token))

        g.token = token
        g.service = service
        g.xrfunc = xrfunc
        return f(*args, **kwargs)

    return wrap


def dec_handle_payment(f):
    """Submits the payment for the xrouter call if payment enforcement is enabled
    on the requested endpoint. If the default xrouter payment enforcement is
    used the payment submission is handled on a background thread. For non-default
    payment enforcement endpoints, the payment is sent on the active thread and
    blocks until the payment endpoint returns a response."""
    @wraps(f)
    def wrap(*args, **kwargs):
        # if payment tx exists, process it in background
        payment_tx = str(request.environ.get('HTTP_XR_PAYMENT', ''))
        should_handle = payment_enforcement = uwsgi.opt.get('HANDLE_PAYMENTS_' + g.token, b'').decode('utf8').lower()
        logging.debug('paymentenforce: {} token: {}'.format(payment_enforcement, g.token))

        if should_handle == 'true' or should_handle == '1':
            if payment_enforcement == 'true' or payment_enforcement == '1':
                if payment_tx == '' or not handle_payment(payment_tx, request.environ):
                    return send_response({
                        'code': 1028,
                        'error': 'Bad request: bad or insufficient fee for ' + g.xrfunc + ' for token ' + g.token
                    }, config.get_snodekey())
            else:
                hp_thread = threading.Thread(target=handle_payment, args=(payment_tx, request.environ))
                hp_thread.start()

        return f(*args, **kwargs)

    return wrap


def handle_payment(payment_tx: str, env: dict):
    """Submits the payment transaction to the configured payment processor endpoint."""
    rpchost = uwsgi.opt.get('HANDLE_PAYMENTS_RPC_HOSTIP', b'').decode('utf8')
    rpcport = uwsgi.opt.get('HANDLE_PAYMENTS_RPC_PORT', b'').decode('utf8')
    rpcuser = uwsgi.opt.get('HANDLE_PAYMENTS_RPC_USER', b'').decode('utf8')
    rpcpass = uwsgi.opt.get('HANDLE_PAYMENTS_RPC_PASS', b'').decode('utf8')
    rpcver = uwsgi.opt.get('HANDLE_PAYMENTS_RPC_VER', b'1.0').decode('utf8')
    rpcurl = 'http://' + rpcuser + ':' + rpcpass + '@' + rpchost + ':' + rpcport
    if rpcuser == '' and rpcpass == '':  # if no rpc credentials
        rpcurl = 'http://' + rpchost + ':' + rpcport

    client_pubkey = str(env.get('HTTP_XR_PUBKEY', b''))

    params = [payment_tx]
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({
        'id': 1,
        'method': 'sendrawtransaction',
        'params': params,
        'jsonrpc': rpcver
    })

    try:
        res = requests.post(rpcurl, headers=headers, data=payload)
        enforce = uwsgi.opt.get('HANDLE_PAYMENTS_ENFORCE', b'false').decode('utf8')
        # look for valid tx hash in response otherwise fail the check
        if enforce == 'true' or enforce == '1':
            payment_response = res.content.decode('utf8')
            if len(payment_response) != 32 or 'error' in payment_response:
                logging.info('Failed to process payment from client: {} Error: {} tx hex: {}',
                             client_pubkey, payment_response, payment_tx)
                return False
        logging.info('Successfully processed payment from client: {} BLOCK tx: {}', client_pubkey, payment_tx)
        return True
    except:
        logging.error('Failed to process payment from client: {} BLOCK tx: {}', client_pubkey, payment_tx)
        return False
