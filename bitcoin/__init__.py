# Copyright (C) 2012-2018 The python-bitcoinlib developers
#
# This file is part of python-bitcoinlib.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-bitcoinlib, including this file, may be copied, modified,
# propagated, or distributed except according to the terms contained in the
# LICENSE file.

from __future__ import absolute_import, division, print_function, unicode_literals

import bitcoin.core

# Note that setup.py can break if __init__.py imports any external
# dependencies, as these might not be installed when setup.py runs. In this
# case __version__ could be moved to a separate version.py and imported here.
__version__ = '0.11.0dev'

class MainParams(bitcoin.core.CoreMainParams):
    MESSAGE_START = b'\xf9\xbe\xb4\xd9'
    DEFAULT_PORT = 41412
    RPC_PORT = 41414
    DNS_SEEDS = ()
    BASE58_PREFIXES = {'PUBKEY_ADDR':26,
                       'SCRIPT_ADDR':28,
                       'SECRET_KEY' :154}
    BECH32_HRP = 'block'

class TestNetParams(bitcoin.core.CoreTestNetParams):
    MESSAGE_START = b'\x0b\x11\x09\x07'
    DEFAULT_PORT = 41474
    RPC_PORT = 41419
    DNS_SEEDS = ()
    BASE58_PREFIXES = {'PUBKEY_ADDR':139,
                       'SCRIPT_ADDR':19,
                       'SECRET_KEY' :239}
    BECH32_HRP = 'tblock'

class RegTestParams(bitcoin.core.CoreRegTestParams):
    MESSAGE_START = b'\xfa\xbf\xb5\xda'
    DEFAULT_PORT = 41489
    RPC_PORT = 41499
    DNS_SEEDS = ()
    BASE58_PREFIXES = {'PUBKEY_ADDR':139,
                       'SCRIPT_ADDR':19,
                       'SECRET_KEY' :239}
    BECH32_HRP = 'blockrt'

"""Master global setting for what chain params we're using.

However, don't set this directly, use SelectParams() instead so as to set the
bitcoin.core.params correctly too.
"""
#params = bitcoin.core.coreparams = MainParams()
params = MainParams()

def SelectParams(name):
    """Select the chain parameters to use

    name is one of 'mainnet', 'testnet', or 'regtest'

    Default chain is 'mainnet'
    """
    global params
    bitcoin.core._SelectCoreParams(name)
    if name == 'mainnet':
        params = bitcoin.core.coreparams = MainParams()
    elif name == 'testnet':
        params = bitcoin.core.coreparams = TestNetParams()
    elif name == 'regtest':
        params = bitcoin.core.coreparams = RegTestParams()
    else:
        raise ValueError('Unknown chain %r' % name)
