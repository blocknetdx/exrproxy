# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

import os
from pony.orm import *

db = Database(provider='postgres',
              host=os.environ['DB_HOST'],
              user=os.environ['DB_USERNAME'],
              password=os.environ['DB_PASSWORD'],
              database=os.environ['DB_DATABASE'])
