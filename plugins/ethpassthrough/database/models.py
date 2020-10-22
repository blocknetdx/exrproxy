# Copyright (c) 2020 The Blocknet developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from datetime import datetime
from pony.orm import *
from plugins.ethpassthrough.database.db import db


class Project(db.Entity):
    name = PrimaryKey(str)

    api_key = Required(str)
    api_token_count = Required(int)
    used_api_tokens = Optional(int, sql_default=0)

    expires = Optional(datetime)
    payments = Set(lambda: Payment, reverse='project')

    active = Required(bool, sql_default=False)


class Payment(db.Entity):
    pending = Required(bool)
    address = Required(str)

    tx_hash = Optional(str)
    amount = Optional(float)
    start_time = Required(datetime)

    project = Required(Project, reverse='payments')


db.generate_mapping(create_tables=True)
