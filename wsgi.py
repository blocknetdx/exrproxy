# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import logging
import os
import importlib

import uwsgi
from flask import Flask
import bitcoin.wallet
from exr import config
from plugins import app as webapp, xrouter
from plugins import limiter

app = Flask('main')
limiter.init_app(app)
app.register_blueprint(webapp)
app.register_blueprint(xrouter.app)

# logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(level=LOGLEVEL,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    datefmt='[%Y-%m-%d:%H:%M:%S]')

def load_plugins():
    """Load EXR plugins"""
    plugins = uwsgi.opt.get('PLUGINS', b'').decode('utf8').split(',')

    for plugin in plugins:
        if 'evm_passthrough_' in plugin or 'xquery_' in plugin: continue # these are not real plugins
        try:
            plugin_app = getattr(importlib.import_module(f"plugins.{plugin}.routes"), "app")
            app.register_blueprint(plugin_app)
        except Exception as e:
            logging.error(f'Failed to load {plugin} plugin: {e}')


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
