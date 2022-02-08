# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import json
import logging
import os
import threading

import requests
from flask import Blueprint, jsonify, request 
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
<h1>projects is supported on this host</h1>
<div>
  To get started create a project:
  curl -X POST -d \'{"id": 1, "method": "request_project", "params": []}\' http://host:port/xrs/projects
</div>
<div>
  To list all projects:
  curl -X POST -d \'{"id": 1, "method": "list_projects", "params": []}\' http://host:port/xrs/projects
</div>
    '''


@app.route('/xrs/projects', methods=['POST'])
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
    
    if 'method' in json_data and json_data['method'] == 'list_projects':
        project = req_handler.list_projects()
        logging.info('Project Requested: {}'.format(project))
        return jsonify(project)

    return projects_root()
