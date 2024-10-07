# Copyright (C) JackTEK 2018-2020
# -------------------------------

import datetime

# ========================
# Import PATH dependencies
# ========================
# ------------------------
# Third-party dependencies
# ------------------------
from custos import blueprint


class User(blueprint):
    def __init__(self,
                 **user_data: dict):
        self.username = user_data.pop("username")
        self.password = user_data.pop("password")

        self.admin = user_data.pop("admin")
        self.token = user_data.pop("token")

        self.id = user_data.pop("id")
        self.created_at = user_data.pop("created_at")

        self.created_at_friendly = self.created_at.strftime("%d/%m/%Y %H:%M")


class File(blueprint):
    def __init__(self,
                 **file_data: dict):
        self.id = file_data.pop("id")
        self.key = file_data.pop("key")
        self.deleted = file_data.pop("deleted")

        self.created_at = file_data.pop("created_at")

        self.created_at_friendly = self.created_at.strftime("%d/%m/%Y %H:%M")

        self.owner = file_data.pop("owner")


class URL(blueprint):
    def __init__(self,
                 **url_data: dict):
        self.id = url_data.pop("id")
        self.key = url_data.pop("key")
        self.url = url_data.pop("url")

        print('DEBUG PRE  url_data %r' % url_data)
        self.created_at = url_data.pop("created_at")
        # FIXME without correct types/sqlite mapping get a string and NOT a datetime
        if isinstance(self.created_at, str):
            #self.created_at = datetime.datetime(self.created_at)
            d = self.created_at
            self.created_at = datetime.datetime(*map(int, d.replace('.', ' ').replace(':', ' ').replace('-', ' ').split()))  # FIXME find my other code for this
        print('DEBUG POST url_data %r' % url_data)
        print('DEBUG self.created_at %r' % self.created_at)

        self.created_at_friendly = self.created_at.strftime("%d/%m/%Y %H:%M")

        self.owner = url_data.pop("owner")