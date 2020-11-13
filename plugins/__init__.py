# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from flask import Blueprint

app = Blueprint('exr', __name__)


@app.route('/', methods=['GET', 'POST', 'HEAD'])
def a():
    return info()


@app.route('/xr', methods=['GET', 'POST', 'HEAD'])
def b():
    return info()


@app.route('/xrs', methods=['GET', 'POST', 'HEAD'])
def c():
    return info()


@app.route('/xr/', methods=['GET', 'POST', 'HEAD'])
def d():
    return info()


@app.route('/xrs/', methods=['GET', 'POST', 'HEAD'])
def e():
    return info()


def info():
    return '<h1>Enterprise XRouter host</h1>'
