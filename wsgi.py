# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import logging
import os

import uwsgi
from flask import Flask

import bitcoin.wallet
from exr import config
from plugins import app as webapp, xrouter

app = Flask('main')
app.register_blueprint(webapp)
app.register_blueprint(xrouter.app)

# debugging
# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', port=4444, stdoutToServer=True, stderrToServer=True)

# logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(level=LOGLEVEL,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    datefmt='[%Y-%m-%d:%H:%M:%S]')


def load_plugins():
    """Load EXR plugins"""
    plugins = uwsgi.opt.get('PLUGINS', b'').decode('utf8').split(',')
    if 'eth_passthrough' in plugins:
        try:
            from plugins.ethpassthrough import routes
            app.register_blueprint(routes.app)
        except Exception as e:
            logging.error('Failed to load eth_passthrough plugin: %s', getattr(e, 'message', repr(e)))


# Set the bitcoin library parameters including chain and service node signing key.
if __name__ == 'wsgi':
    logging.debug('### app start')

    # Select chain and add to global config
    chain = uwsgi.opt.get('BLOCKNET_CHAIN', b'mainnet').decode('utf8').strip()
    try:
        bitcoin.SelectParams(chain)
    except ValueError as e:
        logging.error(f'Failed to parse BLOCKNET_CHAIN parameter [{chain}], defaulting to [mainnet]: %s',
                      getattr(e, 'message', repr(e)))
        chain = 'mainnet'
        bitcoin.SelectParams(chain)
    config.set_chain(chain)

    # Check snodekey and add to global config
    snodekey_raw = uwsgi.opt.get('SERVICENODE_PRIVKEY', b'').decode('utf8').strip()
    if not snodekey_raw:
        logging.error('bad service node key')
        exit(1)
    else:
        try:
            key = bitcoin.wallet.CBitcoinSecret(snodekey_raw)
            config.set_snodekey(key)
        except bitcoin.wallet.CBitcoinSecretError as e:
            logging.error('bad service node key: %s', getattr(e, 'message', repr(e)))
            exit(1)

    load_plugins()
