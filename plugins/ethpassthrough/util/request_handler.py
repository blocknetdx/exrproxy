# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import os
import json
import requests


class RequestHandler:
    def __init__(self):
        self.session_eth = requests.Session()
        self.session_payment = requests.Session()
        self.payment_processor_host = os.environ.get('PAYMENT_PROCESSOR_HOST', 'localhost')

    def get_project(self):
        return self.session_payment.get('http://{}/create_project'.format(self.payment_processor_host), timeout=300).json()

    def post_eth_proxy_project(self, host, data, project_id, api_key):
        return self.session_eth.post('http://{}/xrs/eth_passthrough/{}'.format(host, project_id),
                                     headers={
                                         'Content-Type': 'application/json',
                                         'Api-Key': api_key,
                                     },
                                     data=json.dumps(data), timeout=300).json()

    def post_update_api_count(self, project_id):
        return self.session_payment.post('http://{}/{}/api_count'.format(self.payment_processor_host, project_id),
                                         timeout=300)
