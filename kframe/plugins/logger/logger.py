#!/usr/bin/env python3

from collections import deque

from kframe import Plugin
from kframe.plugins.planner import Planener
from kframe.plugins.logger.queries import (
    DDL,
    LOG_ROW,
    INSERT_LOGS,
)


class Logger(Plugin):
    def init(self, **kwargs):
        """
            params:
            scheme - str - SQL scheme for log-table
            log_table - str - name of log-table in SQL
            save_level - list or set - set of log-levels that'll be logged to SQL
            parent_save - bool - if True also save as used to
            use_queue - bool - if True keep logs in queue and insert several at once
            max_queue_size - int - max size of queue
            use_planner - bool - if True use planner for inserting logs
            planner_timeout - int - num of secs how often check queue for updates
        """
        try:
            if 'sql' not in self:
                self.errmsg = 'logger: sql must be already initialized'
                self.FATAL = True
                return
            scheme = kwargs['scheme'] if 'scheme' in kwargs else self.P.sql.cfg['scheme']
            if scheme is None:
                raise ValueError('Expected "scheme" as param of SQL or Logger')
            defaults = {
                'save_level': {'warning', 'error', 'critical'},
                'parent_save': True,
                'scheme': scheme,
                'log_table': 'log',
                'max_queue_size': 10,
                'use_planner': False,
                'use_queue': True,
                'planner_timeout': 15,
            }
            self.cfg = {k: kwargs[k] if k in kwargs else defaults[k] for k in defaults}
            self._queue = deque()
            flag, e = self.P.sql.create_table(ddl={'log_table': DDL.format(**self.cfg)})
            if not flag:
                raise e
            self._parent_function = self.P.save_log

            if self.cfg['use_planner']:
                if 'planner' not in self:
                    self.P.fast_init(
                        key='planner',
                        target=Planener,
                        export=False,
                    )
                if not self.P.planner.registrate(
                    key='logger-push',
                    target=self.planner_callback,
                    sec=self.cfg['planner_timeout'],
                ):
                    self.errmsg = 'logger: failed to registrate task in planner'
                    self.FATAL = True

        except Exception as e:
            self.errmsg = 'logger: {}'.format(e)
            self.FATAL = True

    def _push(self, rows):
        """
            push data to SQL
        """
        query = INSERT_LOGS(
            scheme=self.cfg['scheme'],
            log_table=self.cfg['log_table'],
            rows=rows,
        )
        return self.P.execute(query)[0]

    def planner_callback(self):
        """
            hook for Kframe.plugins.Planner
        """
        if len(self._queue) > 0 and self._push(self._queue):
            self._queue.clear()

    def new_save_log(self, message, raw_msg, time, level, user_prefix):
        """
            hook for Kframe.base.Parent
        """
        if level in self.cfg['save_level']:
            row = LOG_ROW(
                author=self.P.name,
                level=level,
                message=message,
            )
            if self.cfg['use_queue']:
                self._queue.append(row)
                if len(self._queue) > self.cfg['max_queue_size'] and self._push(self._queue):
                    self._queue.clear()
            else:
                self._push([row])

        if self.cfg['parent_save']:
            self._parent_function(
                message=message,
                raw_msg=raw_msg,
                time=time,
                level=level,
                user_prefix=user_prefix,
            )

    def start(self):
        """
            alya overwrite parent's method
        """
        self.P.save_log = self.new_save_log
