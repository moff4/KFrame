#!/usr/bin/env python3

import time
import sys


class BaseLogger:

    # how to show user time (str)
    SHOW_TIME_FORMAT = '%d.%m.%Y %H:%M:%S'

    defaults = {
        'log_file': 'log.txt',
    }

    def __init__(self, parent, **kwargs):
        self. P = parent
        self.cfg = {k: kwargs.get(k, self.defaults[k]) for k in self.defaults}
        self._hooks = {}

        self.levels = {
            'debug': 'Debug',
            'info': 'Info',
            'warning': 'Warning',
            'error': 'Error',
            'critical': 'Critical',
        }

    def save_log(self, message, raw_msg, time, level, user_prefix):
        """
            save log message to file
            and call hooks
        """
        errmsg = []
        for key in self._hooks:
            try:
                hook = self._hooks[key]
                if level in hook['levels']:
                    hook['target'](
                        message=message,
                        raw_msg=raw_msg,
                        time=time,
                        level=level,
                        user_prefix=user_prefix,
                        **hook['kwargs']
                    )
            except Exception as e:
                errmsg.append(e)

        if '--no-log' not in self.P.argv:
            with open(self.cfg['log_file'], 'ab') as f:
                f.write(''.join([message, '\n']).encode('utf-8'))
                for message in errmsg:
                    f.write(''.join([message, '\n']).encode('utf-8'))

    def log(self, st, _type='info', force=False, plugin_name=None):
        """
            log function
            st - message to save
             _type    |   level
            'debug'   |   Debug
            'info'    |   Info - default
            'warning' |   Warning
            'error'   |   Error
            'critical'|   Critical
        """
        _type = _type if _type in self.levels else 'error'
        prefix = self.levels[_type]
        _time = time.localtime()
        msg = '{_time} -:- {prefix} : {raw_msg}'.format(
            _time=time.strftime(self.SHOW_TIME_FORMAT, _time),
            prefix=prefix,
            raw_msg=st,
        )
        if (
            _type == 'debug'
        ) and not (
            '--debug' in self.P.argv or force or '--debug-{}'.format(plugin_name) in self.P.argv
        ):
            return self
        if '--stdout' in self.P.argv:
            sys.stdout.write(''.join([msg, '\n']))
        self.save_log(
            message=msg,
            raw_msg=st,
            time=_time,
            level=_type,
            user_prefix=prefix
        )
        return self

    def add_log_level(self, key, user_prefix):
        """
            add new level of logging
        """
        self.levels[key] = user_prefix

    def add_hook(self, target, key, levels=None, extra_hook_kwargs=None):
        if not callable(target):
            raise TypeError('Target must be callable')
        self._hooks[key] = {
            'target': target,
            'levels': set(self.levels.keys()) if levels is None else levels,
            'kwargs': {} if extra_hook_kwargs is None else extra_hook_kwargs,
        }

    def upd_hook(self, key, **kwargs):
        if key not in self._hooks:
            raise ValueError('Unregistrated log hook: {}', key)
        self._hooks[key].update(
            {
                i: kwargs.get(i, self._hooks[key][i])
                for i in self._hooks[key]
            }
        )

    def del_hook(self, key):
        self._hooks.pop(key, None)
