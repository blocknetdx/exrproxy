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
        project = req_handler.get_project()
        logging.info('Project Requested: {}'.format(project))
        return jsonify(project)
    
    return projects_root()

@app.route('/xrs/projects/<project_id>', methods=['POST'])
@app.route('/xrs/projects/<project_id>/', methods=['POST'])
@half_authenticate
def project_stats_call(project_id):
    try:
        json_data = request.get_json(force=True)
    except Exception as e:
        logging.debug(e)
        return bad_request_error('malformed json post data')

    if 'method' in json_data and json_data['method'] == 'get_project_stats':
        # Note: project.expires only evaluates to True if project was activated by full payment being received
        status = "user cancelled" if g.project.user_cancelled \
            else "pending" if g.payment.pending and not g.project.active and datetime.datetime.now() < g.payment.start_time + datetime.timedelta(hours=1) \
            else "active" if g.project.active and g.project.expires and g.project.used_api_tokens < g.project.api_token_count and datetime.datetime.now() <= g.project.expires \
            else "inactive" if not g.project.active and g.project.expires and (g.project.used_api_tokens >= g.project.api_token_count or datetime.datetime.now() > g.project.expires) \
            else "cancelled"
        project = {
            "error": 0,
            "result":
              {
                "project_id": project_id,
                "api_key": g.project.api_key,
                "status": status,
                "tier": 0 if status == "pending" else 2 if g.project.archive_mode else 1,
                "api_tokens": str(g.project.api_token_count) if g.project.expires else "N/A",
                "api_tokens_used": str(g.project.used_api_tokens) if g.project.expires else "N/A",
                "api_tokens_remaining": str(g.project.api_token_count - g.project.used_api_tokens) if g.project.expires else "N/A",
                "expiry_time": (g.payment.start_time + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "expiration_date": g.project.expires.strftime("%Y-%m-%d %H:%M:%S UTC") if g.project.expires else "N/A",
                "eth_address": str(g.payment.eth_address),
                "avax_address": str(g.payment.avax_address),
                "nevm_address": str(g.payment.nevm_address),
                "tier1_expected_amount_eth": str(g.payment.tier1_expected_amount_eth),
                "tier2_expected_amount_eth": str(g.payment.tier2_expected_amount_eth),
                "tier1_expected_amount_ablock": str(g.payment.tier1_expected_amount_ablock),
                "tier2_expected_amount_ablock": str(g.payment.tier2_expected_amount_ablock),
                "tier1_expected_amount_aablock": str(g.payment.tier1_expected_amount_aablock),
                "tier2_expected_amount_aablock": str(g.payment.tier2_expected_amount_aablock),
                "tier1_expected_amount_sysblock": str(g.payment.tier1_expected_amount_sysblock),
                "tier2_expected_amount_sysblock": str(g.payment.tier2_expected_amount_sysblock),
                "tier1_expected_amount_wsys": str(g.payment.tier1_expected_amount_wsys),
                "tier2_expected_amount_wsys": str(g.payment.tier2_expected_amount_wsys),
                #"tx_hash": str(g.payment.tx_hash) if g.project.expires else "N/A",  # tx_hash is never set in eth-payment-processor!
                "amount_eth": str(g.payment.amount_eth) if g.project.expires else "N/A",
                "amount_ablock": str(g.payment.amount_ablock) if g.project.expires else "N/A",
                "amount_aablock": str(g.payment.amount_aablock) if g.project.expires else "N/A",
                "amount_sysblock": str(g.payment.amount_sysblock) if g.project.expires else "N/A",
                "amount_wsys": str(g.payment.amount_wsys) if g.project.expires else "N/A",
                "start_time": g.payment.start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
              }
        }
        logging.info('Project Stats: {}'.format(project))
        return jsonify(project)

    return projects_root()


