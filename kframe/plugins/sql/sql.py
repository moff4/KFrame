#!/usr/bin/env python3

import mysql.connector as sql

from kframe.base.plugin import Plugin


class SQL(Plugin):
    """
        kwargs:
            scheme - str
            DDL - dict : tablename(str) => DDL script for creating(str)
    """

    name = 'sql'
    defaults = {
        'ddl': [],
    }

    def init(self, host, port, user, passwd, **kwargs):
        try:
            self.cfg.update(
                {
                    'host': host,
                    'port': port,
                    'user': user,
                    'passwd': passwd,
                    'scheme': None,
                }
            )
            self.conn = None
            self._lock = 0

            self.FATAL = not self.connect()
            if self.FATAL:
                self.errmsg = "could not connect to SQL-server"
            self.close()
        except Exception as e:
            self.FATAL = True
            self.errmsg = str(e)

    def __del__(self):
        self.close()

# ==========================================================================
#                                INTERNAL METHODS
# ==========================================================================

    def __connect(self):
        params = {}
        for i in ['user', 'passwd', 'host', 'port']:
            params[i] = self.cfg[i]
        if self.cfg['scheme']:
            params['db'] = self.cfg['scheme']
        return sql.connect(**params)

    def connect(self):
        """
            open connection
        """
        try:
            self.conn = self.__connect()
            self._lock += 1
            return True
        except Exception as e:
            self.Error('connect-error: ({user}@{host}:{port}/{scheme}): {ex}'.format(
                user=self.cfg['user'],
                host=self.cfg['host'],
                port=self.cfg['port'],
                scheme=self.cfg['scheme'] if self.cfg['scheme'] else "",
                ex=e
            ))
            return False

    def close(self, _all=False):
        """
            close connection
        """
        if _all:
            self._lock = 0
        else:
            self._lock -= 1
        if self._lock <= 0:
            self._lock = 0
            try:
                self.conn.close()
            except Exception:
                pass

    def reconnect(self):
        """
            reopen connection to database
        """
        try:
            self.close()
            self.connect()
        except Exception as e:
            self.Error('reconnect-error: {}', e)

    def create_table(self, ddl=None):
        """
            create all tables according to there DDL (dict or list of CREATE TABLE scripts)
            return tuple ( True in case of success or False , None or Exception)
        """
        boo = True
        try:
            if ddl is None:
                ddl = self.cfg.get('ddl', None)
            if ddl is not None:
                for i in ddl.values() if isinstance(ddl, dict) else ddl:
                    boo &= self.execute(i, commit=True)[0]
                self.Debug('All tables created: {}', boo)
            return True, None
        except Exception as e:
            self.Error("create-table: {}".format(e))
            return False, e

# ==========================================================================
#                                USER API
# ==========================================================================

    def execute(self, query, commit=False, multi=False):
        """
            exec query
            universal method: select/create/insert/update/...
            return tuple( flag of success , data as list of tuples )
        """
        res = []
        boo = True
        try:
            if not self.conn.is_connected():
                self.reconnect()
            if self.conn is not None and self.conn.is_connected():
                cu = self.conn.cursor()
                cu.execute(query, multi=multi)
                res = []
                try:
                    res = cu.fetchall()
                except Exception as e:
                    pass
                if commit:
                    try:
                        self.conn.commit()
                    except Exception:
                        pass
            else:
                boo = False
        except Exception as e:
            self.Error('exec-query: {ex}', ex=e)
            boo = False
        return boo, res

    def select_all(self, query, *args, **kwargs):
        """
            method specialy for select
            return list of tuples (rows) in case of success
            or None in case of error
        """
        try:
            query = query.format(*args, **kwargs)
            if not self.conn.is_connected():
                self.reconnect()
            if self.conn is not None and self.conn.is_connected():
                cu = self.conn.cursor()
                cu.execute(query)
                res = cu.fetchall()
                return res
        except Exception as e:
            self.Error('select-all: {ex}', ex=e)
            return None

    def select(self, query, *args, **kwargs):
        """
            method specialy for select
            return generator that returns tuples (row) in case of success
            or raise Exception in case of error
        """
        try:
            query = query.format(*args, **kwargs)
            if not self.conn.is_connected():
                self.reconnect()
            if self.conn is not None and self.conn.is_connected():
                cu = self.conn.cursor()
                cu.execute(query)
                while True:
                    res = cu.fetchone()
                    if res is None:
                        break
                    yield res
        except Exception as e:
            self.Error('select-one: {ex}', ex=e)
            raise

    def start(self):
        self.create_table()
