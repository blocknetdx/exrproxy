# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import datetime
import logging
from enum import IntEnum
from functools import wraps
from flask import g, request, jsonify
from plugins.ethpassthrough.database.models import db_session, Project


class ApiError(IntEnum):
    MISSING_API_KEY = 1
    MISSING_PROJECT_ID = 2
    PROJECT_NOT_EXIST = 3
    PROJECT_EXPIRED = 4
    API_TOKENS_EXCEEDED = 5
    MISSING_PAYMENT = 6
    API_KEY_DISABLED = 7


def missing_keys():
    response = jsonify({
        'message': "API_KEY header missing or project-id missing",
        'error': ApiError.MISSING_KEYS
    })

    return response, 401


def project_not_exists():
    response = jsonify({
        'message': "Bad API_KEY or project-id does not exist",
        'error': ApiError.PROJECT_NOT_EXIST
    })

    return response, 401


def project_expired():
    response = jsonify({
        'message': "Project has expired",
        'error': ApiError.PROJECT_EXPIRED
    })

    return response, 401


def api_tokens_exceeded():
    response = jsonify({
        'message': "API calls exceeded!",
        'error': ApiError.API_TOKENS_EXCEEDED
    })

    return response, 401


def api_key_disabled():
    response = jsonify({
        'message': "API key is disabled",
        'error': ApiError.API_KEY_DISABLED
    })
    return response, 401


def api_error_msg(msg: str, code: ApiError):
    response = jsonify({
        'message': msg,
        'error': code
    })

    return response, 401


def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        logging.debug('%s %s', request.headers.get('Api-Key'), request.view_args['project_id'])
        if 'help' not in request.base_url:
            if 'Api-Key' not in request.headers:
                return api_error_msg('Missing Api-Key header', ApiError.MISSING_API_KEY)
        if 'project_id' not in request.view_args:
            return api_error_msg('Missing project-id in url', ApiError.MISSING_PROJECT_ID)

        project_id = request.view_args['project_id']
        if 'help' not in request.base_url:
            api_key = request.headers.get('Api-Key')

        with db_session:
            if 'help' in request.base_url:
                project = Project.get(name=project_id)
            else:
                project = Project.get(name=project_id, api_key=api_key)

        if project is None:
            return project_not_exists()

        if not project.expires:
            return api_error_msg('Payment not received yet. Please submit payment or wait until payment confirms',
                                 ApiError.MISSING_PAYMENT)

        if datetime.datetime.now() > project.expires or not project.active:
            return api_error_msg('Project has expired. Please request a new project and api key',
                                 ApiError.PROJECT_EXPIRED)

        if project.used_api_tokens >= project.api_token_count:
            return api_tokens_exceeded()

        if not project.active:
            return api_key_disabled()

        g.project = project

        return f(*args, **kwargs)
    return wrapper
