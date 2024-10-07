# Copyright (C) JackTEK 2018-2020
# -------------------------------
# This is the main file, only ever run this file.

# Introduction to commenting
# --------------------------
# All comments within these files will be surrounded by lines to make them stand out.

# = top level/vague overview
# - lower level/more specific explanation
# ~ notes or explanation of a small amount of code

# Incomplete or WIP sections of code will also use the following formatting:
# ! = something here is being or has been deprecated
# ? = query in place about something
# * = version note
# TODO = details something that needs to be done
# REF = references something to previous comment
# TEMPORARY = indicates that this line or lines of code is temporary

# =====================
# Import PATH libraries
# =====================
# ------------
# Type imports
# ------------
from typing import Optional


# -----------------
# Builtin libraries
# -----------------
import os.path

from atexit import register
from contextlib import closing
from os import _exit, listdir, makedirs
from platform import system
from sys import argv


from wsgiref.simple_server import make_server

try:
    import bjoern
except ImportError:
    bjoern = None

try:
    import cheroot  # CherryPy Server https://cheroot.cherrypy.dev/en/latest/pkg/cheroot.wsgi/
except ImportError:
    cheroot = None

try:
    import meinheld  # https://github.com/mopemope/meinheld
except ImportError:
    meinheld = None


# ------------------------
# Third-party dependencies
# ------------------------
from flask import Flask
#from gevent.pywsgi import WSGIServer
from pyfiglet import FontNotFound, print_figlet

try:
    import psycopg2
except ImportError:
    psycopg2 = None
#from psycopg2 import connect
#import sqlite3
import sqlite3_paramstyle as sqlite3  # FIXME name

# -------------------------
# Local extension libraries
# -------------------------
import util.utilities as utils

from custos import blueprint

from util import console, constants
from util.constants import cache, config
from util.blueprints import File, URL, User


constants.app = app = Flask(import_name="Imago")


class Imago(blueprint):
    def on_exit(self):
        """This runs some code before we quietly close down."""
        
        console.fatal(text="Shutting down...")
        self.print_fig(stop=True)

    def print_fig(self,
                  stop: Optional[bool] = False):
        """Prints either the startup or shutdown Figlet depending on the value of stop."""

        local_config = config.figlet

        try:
            print_figlet(text=local_config.stop if stop else local_config.start,
                         width=local_config.width,
                         font=local_config.font)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # the configured font doesn't exist, so we force a change 
        # to the loaded config and send a warning message to the console 
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        except FontNotFound:
            console.warn(text=f"{local_config.font} font not found, fixing.")
            
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # attrdict creates shallow copies internally when we access it
            # using the attribute syntax, so we have to use the key syntax
            # to be able to edit the attributes
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            config["figlet"]["font"] = "standard"

            print_figlet(text=local_config.stop if stop else local_config.start,
                         width=local_config.width,
                         font="standard")

    def postgres_init(self):
        """Initialises the connection to the PostgreSQL server."""

        constants.database_connection = psycopg2.connect(dsn="user={pg.user} password={pg.password} host={pg.host} port={pg.port} dbname={pg.database}".format(pg=config.postgres))
        console.info(text="Connected to Postgres server at: {pg.user}@{pg.host}/{pg.database}".format(pg=config.postgres))
        constants.database_connection.set_session(autocommit=True) # FIXME review this, postgres specific

        # =================================
        # Create the required schema tables
        # =================================
        with constants.database_connection.cursor() as con:
            queries = ("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, admin BOOLEAN, token TEXT, created_at TIMESTAMP);""",
                       """CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, owner_id INT, key TEXT UNIQUE, deleted BOOLEAN, created_at TIMESTAMP);""",
                       """CREATE TABLE IF NOT EXISTS urls (id SERIAL PRIMARY KEY, owner_id INT, key TEXT UNIQUE, url TEXT, created_at TIMESTAMP);""")

            for query in queries:
                con.execute(query)
                constants.database_connection.commit()

            # =================================
            # Populate file, url and user cache
            # =================================
            console.verbose(text="Beginning cache population...")
            console.verbose(text="Populating user cache...")
            query = """SELECT id, username, password, admin, token, created_at
                       FROM users
                       ORDER BY id ASC;"""

            con.execute(query)

            for user in con.fetchall():
                cache["users"].append(User(id=user[0],
                                           username=user[1],
                                           password=user[2],
                                           admin=user[3],
                                           token=user[4],
                                           created_at=user[5]))
                console.verbose(text=f"Populated cache for user {user[0]} ({user[1]}).")

            console.verbose(text="Populating file cache...")
            query = """SELECT id, owner_id, key, deleted, created_at
                       FROM files
                       ORDER BY created_at DESC;"""

            con.execute(query)

            for file in con.fetchall():
                cache["files"].append(File(id=file[0],
                                        key=file[2],
                                        deleted=file[3],
                                        created_at=file[4],
                                        owner=utils.first(iterable=cache["users"],
                                                          condition=lambda user: user.id == file[1])))
                console.verbose(text=f"Populated cache for file {file[0]} ({file[2]}).")

            console.verbose(text="Populating URL cache...")
            query = """SELECT id, owner_id, key, url, created_at
                       FROM urls
                       ORDER BY created_at DESC;"""

            con.execute(query)

            for url in con.fetchall():
                cache["urls"].append(URL(id=url[0],
                                         key=url[2],
                                         url=url[3],
                                         created_at=url[4],
                                         owner=utils.first(iterable=cache["users"],
                                                           condition=lambda user: user.id == url[1])))
                console.verbose(text=f"Populated cache for url {url[0]} ({url[2]}).")
    def sqlite_init(self):
        """Initialises the connection to the SQLite database
        TODO refactor - duplicates postgres_init
        ALSO schema type names?."""

        constants.database_connection = sqlite3.connect("{db.database}".format(db=config.sqlite3))
        console.info(text="Connected to local sqlite3 database {db.database}".format(db=config.sqlite3))
        #constants.database_connection.set_session(autocommit=True)  # postgres specific
        constants.database_connection.autocommit = True

        # =================================
        # Create the required schema tables
        # =================================
        with closing(constants.database_connection.cursor()) as con:
            queries = ("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, admin BOOLEAN, token TEXT, created_at TIMESTAMP);""",
                       """CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, owner_id INT, key TEXT UNIQUE, deleted BOOLEAN, created_at TIMESTAMP);""",
                       """CREATE TABLE IF NOT EXISTS urls (id SERIAL PRIMARY KEY, owner_id INT, key TEXT UNIQUE, url TEXT, created_at TIMESTAMP);""")

            for query in queries:
                con.execute(query)
                constants.database_connection.commit()

            # =================================
            # Populate file, url and user cache
            # =================================
            console.verbose(text="Beginning cache population...")
            console.verbose(text="Populating user cache...")
            query = """SELECT id, username, password, admin, token, created_at
                       FROM users
                       ORDER BY id ASC;"""

            con.execute(query)

            for user in con.fetchall():
                cache["users"].append(User(id=user[0],
                                           username=user[1],
                                           password=user[2],
                                           admin=user[3],
                                           token=user[4],
                                           created_at=user[5]))
                console.verbose(text=f"Populated cache for user {user[0]} ({user[1]}).")

            console.verbose(text="Populating file cache...")
            query = """SELECT id, owner_id, key, deleted, created_at
                       FROM files
                       ORDER BY created_at DESC;"""

            con.execute(query)

            for file in con.fetchall():
                cache["files"].append(File(id=file[0],
                                        key=file[2],
                                        deleted=file[3],
                                        created_at=file[4],
                                        owner=utils.first(iterable=cache["users"],
                                                          condition=lambda user: user.id == file[1])))
                console.verbose(text=f"Populated cache for file {file[0]} ({file[2]}).")

            console.verbose(text="Populating URL cache...")
            query = """SELECT id, owner_id, key, url, created_at
                       FROM urls
                       ORDER BY created_at DESC;"""

            con.execute(query)

            for url in con.fetchall():
                cache["urls"].append(URL(id=url[0],
                                         key=url[2],
                                         url=url[3],
                                         created_at=url[4],
                                         owner=utils.first(iterable=cache["users"],
                                                           condition=lambda user: user.id == url[1])))
                console.verbose(text=f"Populated cache for url {url[0]} ({url[2]}).")

    def boot(self,
             host: Optional[str] = "127.0.0.1",
             port: Optional[int] = 5000):  # FIXME does NOT match default config file
        """This runs any necessary pre-init code and then begins the server session."""
        
        # ===========================
        # Create required directories
        # ===========================
        makedirs(name="static/uploads", 
                 exist_ok=True)
        
        # =====================
        # Register exit handler
        # =====================
        register(self.on_exit)

        if psycopg2:
            # ==============================
            # Initialise Postgres connection
            # ==============================
            try:
                self.postgres_init()

            except Exception as error:
                console.fatal(text="Failed to connect to Postgres at: {pg.user}@{pg.host}/{pg.database}\n\n{error}".format(pg=config.postgres,
                                                                                                                           error=error))
                _exit(status=2)
        else:
            try:
                self.sqlite_init()
            except Exception as error:
                raise  # Custos - FIXME either a shitty logger or set to NOT show useful tracebacks on error :-(
                console.fatal(text="Failed to connect to SQLite at: {db.database}\n\n{error}".format(db=config.sqlite3, error=error))
                _exit(status=2)

        # ==================
        # Initialise plugins
        # ==================
        for plugin in (file[:-3] for file in listdir(path="plugins") if file.endswith(".py")):
            try:
                __import__(name=f"plugins.{plugin}")
                console.verbose(text=f"{plugin} plugin successfully booted.")

            except Exception as error:
                raise  # Custos - FIXME either a shitty logger or set to NOT show useful tracebacks on error :-(
                console.error(text=f"{plugin} plugin failed to boot.\n\n{error}\n\n{error.__cause__}")

                _exit(status=2)

        # =============================
        # Start server and print FIGlet
        # =============================
        console.info(text=f"Server started at: http://{host}:{port}")  # well this is bullshit, wrong port
        self.print_fig()
        console.ready(text=f"Currently running Imago v{constants.version.hash}")


if __name__ == "__main__":
    # =======================================
    # Print version info on request via flags
    # =======================================
    if "-v" in argv or "--version" in argv:
        print("Version Information")
        print("===================")
        print(f"Running Imago v{constants.version.hash}")
        print(f"Latest major update serial: {constants.version.major}")
        print(f"Latest minor update serial: {constants.version.minor}")
        print(f"Latest patch update serial: {constants.version.patch}")
        print(f"Current release channel: {constants.version.release}")
        
        quit()

    Imago().boot()

    # if gevent:....
    #WSGIServer((config.server.host, config.server.port), app, log=None).serve_forever()
    server_port = config.server.port
    server_host = config.server.host  # '0.0.0.0'

    # TODO modjy/Jython
    log = console
    #log.info('server_host: %r', server_host)  # this isn't a real logeger :-(
    log.info('server_host: %r' % server_host)  # this isn't a real logeger :-(
    log.info('server_port: %r' % server_port)
    log.info('http://%s:%r' % (server_host, server_port))
    log.info('http://%s:%r' % ('localhost', server_port))
    if bjoern:
        log.info('Using: bjoern')
        bjoern.run(app, '', server_port)  # FIXME use local_ip?
    elif cheroot:
        # Untested
        server = cheroot.wsgi.Server(('0.0.0.0', server_port), my_crazy_app)  # '' untested for address
        server.start()
    elif meinheld:
        # Untested, Segmentation fault when serving a file :-(
        meinheld.server.listen(('0.0.0.0', server_port))  # does not accept ''
        meinheld.server.run(app)
    else:
        log.info('Using: wsgiref.simple_server')
        #httpd = make_server('', server_port, app)  # FIXME use local_ip?
        httpd = make_server('', server_port, app)  # FIXME use local_ip?
        httpd.serve_forever()

