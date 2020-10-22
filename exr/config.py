# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from bitcoin.wallet import CBitcoinSecret


def set_chain(p: str):
    globals()['chain'] = p


def get_chain() -> str:
    return globals()['chain']


def set_snodekey(p: CBitcoinSecret):
    globals()['snodekey'] = p


def get_snodekey() -> CBitcoinSecret:
    return globals()['snodekey']
