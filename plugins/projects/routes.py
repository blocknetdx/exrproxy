# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os
import threading
import datetime
import requests
from flask import Blueprint, jsonify, request, g
from plugins.projects.middleware import half_authenticate
from plugins.projects.util.request_handler import RequestHandler
from plugins import limiter

quote_valid_hours = 1 # number of hours for which price quote given to client is valid; afterwhich, payments get half API calls

app = Blueprint('projects', __name__)
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


@app.route('/xrs/projects', methods=['HEAD', 'GET'])
def projects_root():
    return '''
<h1>Projects is supported on this host</h1>
<div>
  To get started, create a project:
  curl -X POST -d \'{"id": 1, "method": "request_project", "params": []}\' http://host:port/xrs/projects
</div>
<div>
  <br>
  To see more Project API calls, visit <a href="https://api.blocknet.co/#projects-api-xquery-hydra">https://api.blocknet.co/#projects-api-xquery-hydra</a>
</div>
    '''


@app.route('/xrs/projects', methods=['POST'])
@app.route('/xrs/projects/', methods=['POST'])
def xrouter_call():
    try:
        json_data = request.get_json(force=True)
    except Exception as e:
        logging.debug(e)
        return bad_request_error('malformed json post data')

    if 'method' in json_data and json_data['method'] == 'request_project':
#        logging.warning('Project Requested json_data dump:')
#        logging.warning(json_data)
        params = []
        if 'params' in json_data.keys():
            params = json_data['params']
        project = req_handler.get_project(params)
        logging.info('Project Requested: {}'.format(project))
        return jsonify(project)
    
    return projects_root()

@app.route('/xrs/projects/<project_id>', methods=['POST'])
@app.route('/xrs/projects/<project_id>/', methods=['POST'])
@half_authenticate
def project_id_calls(project_id):
    try:
        json_data = request.get_json(force=True)
    except Exception as e:
        logging.debug(e)
        return bad_request_error('malformed json post data')

    if 'method' in json_data and json_data['method'] == 'extend_project':
#        logging.warning('Project Requested json_data dump:')
#        logging.warning(json_data)
        project = req_handler.extend_project(project_id)
        logging.info('Project Extension Requested: {}'.format(project))
        return jsonify(project)

    if 'method' in json_data and json_data['method'] == 'get_project_stats':
        status = "user cancelled" if g.project.user_cancelled \
            else "pending" if g.payment.pending and not g.project.active \
            else "active-pending" if g.project.active and g.payment.pending \
            else "active" if g.project.active \
            else "inactive" if not g.project.active and g.project.activated \
            else "cancelled"
        project = {
            "error": 0,
            "result":
              {
                "project_id": project_id,
                "api_key": g.project.api_key,
                "XQuery": g.project.xquery,
                "Hydra": g.project.hydra,
                "tier": 0 if not g.project.hydra else 2 if g.project.archive_mode else 1,
                "status": status,
                "api_tokens": g.project.api_token_count,
                "api_tokens_used": g.project.used_api_tokens,
                "api_tokens_remaining": g.project.api_token_count - g.project.used_api_tokens,
                "quote_start_time": g.payment.quote_start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "quote_expiry_time": (g.payment.quote_start_time + datetime.timedelta(hours=quote_valid_hours)).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "eth_address": g.payment.eth_address,
                "avax_address": g.payment.avax_address,
                "nevm_address": g.payment.nevm_address,
                "min_amount_usd": g.payment.min_amount_usd,
                "min_amount_ablock_usd": g.payment.min_amount_ablock_usd,
                "min_amount_aablock_usd": g.payment.min_amount_aablock_usd,
                "min_amount_sysblock_usd": g.payment.min_amount_sysblock_usd,
                "min_amount_eth": g.payment.min_amount_eth,
                "min_amount_ablock": g.payment.min_amount_ablock,
                "min_amount_avax": g.payment.min_amount_avax,
                "min_amount_aablock": g.payment.min_amount_aablock,
                "min_amount_sysblock": g.payment.min_amount_sysblock,
                "min_amount_wsys": g.payment.min_amount_wsys,
                "amount_eth": g.payment.amount_eth,
                "amount_ablock": g.payment.amount_ablock,
                "amount_avax": g.payment.amount_avax,
                "amount_aablock": g.payment.amount_aablock,
                "amount_sysblock": g.payment.amount_sysblock,
                "amount_wsys": g.payment.amount_wsys
              }
        }
        logging.info('Project Stats: {}'.format(project))
        return jsonify(project)

    return projects_root()


