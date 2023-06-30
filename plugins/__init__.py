# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from flask import Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def get_real_remote_address():
    from flask import request
    return request.headers.get('X-Forwarded-For') or request.remote_addr
    
limiter = Limiter(key_func=get_real_remote_address)


app = Blueprint('exr', __name__)
limiter.limit("50/minute;3000/hour;72000/day")(app)


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
