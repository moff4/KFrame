#!/usr/bin/env python3

import time
from functools import reduce
from threading import Thread
from multiprocessing import Process


class Task:
    """
        Single task for planner
    """
    defaults = {
        'hours': 0,
        'min': 0,
        'sec': 0,
        'offset': 0,
        'shedule': [('00:00:00', '23:59:59')],
        'calendar': {},
        'weekdays': {i for i in range(7)},
        'args': [],
        'kwargs': {},
        'threading': False,
        'after': None,
        'times': None,
        'max_parallel_copies': None,
        'enable': True,
    }

    def __init__(self, key, target, **kwargs):
        self.defaults.update(
            {
                'key': key,
                'target': target,
                'created': int(time.time()),
                'updated': int(time.time()),
            }
        )
        self.cfg = {k: kwargs.get(k, self.defaults[k]) for k in self.defaults}
        self._threads = []
        self._last_task = 0
        self.cfg['shedule'] = self._convert_shedule(self.cfg['shedule'])

    def _run(self):
        """
            run task
            (in this thread and this proccess)
        """
        return self.cfg['target'](
            *self.cfg['args'],
            **self.cfg['kwargs']
        )

    @staticmethod
    def _convert_shedule(shedule):
        bz = []
        for i in shedule:
            if len(i) != 2:
                raise ValueError('invalid value of property "shedule": list of pairs')
            az = []
            for j in i:
                j = j.split(':')
                while len(j) < 3:
                    j.append(0)
                if len(j) > 3:
                    raise ValueError('invalid value of property "shedule": (HH[:MM[:SS]])')
                az.append(reduce(lambda x, y: int(x) * 60 + int(y), j))
            bz.append(tuple(az))
        return bz

    def _calendar(self, tm):
            def in_cal(t, cal):
                return t.tm_mon in cal and t.tm_mday in cal[t.tm_mon]
            if (
                self.cfg['calendar'].get('allowed', None) is None
            ) and (
                self.cfg['calendar'].get('disallowed', None) is None
            ):
                return True
            elif (
                self.cfg['calendar'].get('allowed', None) is None
            ) or (
                self.cfg['calendar'].get('disallowed', None) is None
            ):
                if (
                    self.cfg['calendar'].get('disallowed', None) is not None
                ) and (
                    in_cal(tm, self.cfg['calendar']['disallowed'])
                ):
                    return False
                elif (
                    self.cfg['calendar'].get('allowed', None) is not None
                ) and (
                    in_cal(tm, self.cfg['calendar']['allowed'])
                ):
                    return True
            else:
                raise ValueError('expected only "allowed" or "disallowed" in calendar property, not both of them')

    def _shedule(self, t):
        return any(
            map(
                lambda x: x[0] <= t <= x[1],
                self.cfg['shedule'],
            )
        )

    def _weekdays(self, tm):
        return tm.tm_wday in self.cfg['weekdays']

    # =========================================================================
    #                               USER API
    # =========================================================================

    @property
    def key(self):
        return self.cfg['key']

    @key.setter
    def self_setter(self, value):
        if not isinstance(value, type):
            raise ValueError('property "(self" must be type, not {}'.format(type(value)))
        self.cfg['self'] = value

    @property
    def target(self):
        return self.cfg['target']

    @target.setter
    def target_setter(self, value):
        if not callable(value):
            raise ValueError('property "target" must be callable')
        self.cfg['target'] = value

    @property
    def updated(self):
        return self.cfg['updated']

    @property
    def created(self):
        return self.cfg['created']

    @property
    def hours(self):
        return self.cfg['hours']

    @hours.setter
    def hours_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "hours" must be int, not {}'.format(type(value)))
        self.cfg['hours'] = value

    @property
    def min(self):
        return self.cfg['min']

    @min.setter
    def min_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "min" must be int, not {}'.format(type(value)))
        self.cfg['min'] = value

    @property
    def sec(self):
        return self.cfg['sec']

    @sec.setter
    def sec_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "sec" must be int, not {}'.format(type(value)))
        self.cfg['sec'] = value

    @property
    def offset(self):
        return self.cfg['offset']

    @offset.setter
    def offset_setter(self, value):
        if not isinstance(value, type):
            raise ValueError('property "offset" must be type, not {}'.format(type(value)))
        self.cfg['offset'] = value

    @property
    def shedule(self):
        return self.cfg['shedule']

    @shedule.setter
    def shedule_setter(self, value):
        if not isinstance(value, list) and not isinstance(value, tuple):
            raise ValueError('property "shedule" must be list or tuple, not {}'.format(type(value)))
        self.cfg['shedule'] = self._convert_shedule(value)

    @property
    def calendar(self):
        return self.cfg['calendar']

    @calendar.setter
    def calendar_setter(self, value):
        if (
            not isinstance(value, dict)
        ) or (
            len(value) > 1
        ) or (
            (
                len(value) == 1
            ) and (
                next(value.keys()) in {'allowed', 'disallowed'}
            )
        ):
            raise ValueError(
                'property "calendar" must be dict with key "allowed" or "disallowed", not {}'.format(
                    type(value)
                )
            )
        self.cfg['calendar'] = value

    @property
    def weekdays(self):
        return self.cfg['weekdays']

    @weekdays.setter
    def weekdays_setter(self, value):
        if (
            not isinstance(value, list) and not isinstance(value, tuple)
        ) or (
            not all(map(lambda x: isinstance(x, int) and 0 <= x <= 7, value))
        ):
            raise ValueError('property "weekdays" must be list or tuple of ints [0..6], not {}'.format(type(value)))
        self.cfg['weekdays'] = value

    @property
    def args(self):
        return self.cfg['args']

    @args.setter
    def args_setter(self, value):
        if not isinstance(value, list) and not isinstance(value, tuple):
            raise ValueError('property "args" must be list or tuple, not {}'.format(type(value)))
        self.cfg['args'] = value

    @property
    def kwargs(self):
        return self.cfg['kwargs']

    @kwargs.setter
    def kwargs_setter(self, value):
        if not isinstance(value, dict):
            raise ValueError('property "kwargs" must be dict, not {}'.format(type(value)))
        self.cfg['kwargs'] = value

    @property
    def threading(self):
        return self.cfg['threading']

    @threading.setter
    def threading_setter(self, value):
        vars = {'thread', 'threading', True, 'process', 'processing'}
        if not isinstance(value, str) or value not in vars:
            raise ValueError('property "threading" must be one of {}, not {}'.format(vars, type(value)))
        self.cfg['threading'] = value

    @property
    def after(self):
        return self.cfg['after']

    @after.setter
    def after_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "after" must be int, not {}'.format(type(value)))
        self.cfg['after'] = value

    @property
    def times(self):
        return self.cfg['times']

    @times.setter
    def times_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "times" must be int, not {}'.format(type(value)))
        self.cfg['times'] = value

    @property
    def max_parallel_copies(self):
        return self.cfg['max_parallel_copies']

    @max_parallel_copies.setter
    def max_parallel_copies_setter(self, value):
        if not isinstance(value, int):
            raise ValueError('property "max_parallel_copies" must be int, not {}'.format(type(value)))
        self.cfg['max_parallel_copies'] = value

    @property
    def enable(self):
        return self.cfg['enable']

    @enable.setter
    def enable_setter(self, value):
        if not isinstance(value, bool):
            raise ValueError('property "enable" must be bool, not {}'.format(type(value)))
        else:
            self.cfg['enable'] = value

    def __getitem__(self, key):
        return self.cfg[key]

    def __contains__(self, key):
        return key in self.cfg

    def __setitem__(self, key, value):
        """
            key must be in self.defaults
        """
        if key in self.defaults:
            self.cfg[key] = value
        else:
            raise KeyError('unsupported key')

    def update(self, *args, **kwargs):
        """
            update task properties
            can be passed dict as argv
            or kwargs
        """
        cfg = {}
        for arg in args:
            if not isinstance(arg, dict):
                raise ValueError('arg must be dict isinstance')
            cfg.update(arg)
        cfg.update(kwargs)
        if 'shedule' in cfg:
            cfg['shedule'] = self._convert_shedule(cfg['shedule'])
        self.cfg.update(kwargs)

    def ready_for_run(self, t, tm):
        """
            t - time in seconds as int (0 .. 86400)
            tm - time_structure from time (like result of time.localtime())
        """
        return all([
            self.cfg['enable'],
            self.cfg['after'] is None or self.cfg['after'] <= time.time(),
            self.cfg['times'] is None or self.cfg['times'] > 0,
            self._calendar(tm),
            self._shedule(t),
            self._weekdays(tm),
        ])

    def seconds_left(self, t):
        """
            t - current time in seconds as int (0 .. 86400)
            return number of seconds left before timeout (excludign filters such as shedule)
        """
        _t = (self.cfg['hours'] * 60 + self.cfg['min']) * 60 + self.cfg['sec']
        return _t - ((t - self.cfg['offset']) % (_t))

    def to_dict(self):
        """
            return all properties as dict
        """
        conv_map = {
            int: lambda x: x,
            float: lambda x: x,
            str: lambda x: x,
            dict: lambda x: {y: conv_map[type(x[y])](x[y]) if type(x[y]) in conv_map else str(x[y]) for y in x},
            list: lambda x: [conv_map[type(y)](y) if type(y) in conv_map else str(y) for y in x],
            set: lambda x: [conv_map[type(y)](y) if type(y) in conv_map else str(y) for y in x],
        }
        return {
            i:
            conv_map[type(self.cfg[i])](self.cfg[i]) if type(self.cfg[i]) in conv_map else str(self.cfg[i])
            for i in self.cfg
        }

    def check_threads(self):
        """
            check threads and process if any complite
        """
        az = []
        for i in self._threads:
            if i[0].is_alive():
                az.append(i)
            else:
                i[0].join()
        self._threads = az

    def get_running_tasks(self):
        """
            timestamps of starts of all parallel running tasks
            return list of int
        """
        return [
            i[1]
            for i in self._threads
        ]

    def run(self, unplanned=False):
        """
            method to start task
            in this method proccess with be forked or threaded if requeried
            return tuple(code as str, msg as str, proc/thread object or None)
        """
        try:
            t = int(time.time())
            if self._last_task == t and unplanned:
                return (
                    'error',
                    'already started',
                )

            self._last_task = t

            if self.cfg['times'] is not None and not unplanned:
                self.cfg['times'] -= 1

            if (
                self.cfg['threading']
            ) and (
                self.cfg['max_parallel_copies'] is not None
            ) and (
                len(self._threads) >= self.cfg['max_parallel_copies']
            ):
                return (
                    'error',
                    'too many running copies of task "{key}"'.format(key=self.cfg['key']),
                )

            if self.cfg['threading']:
                if self.cfg['threading'] in {'thread', 'threading', True}:
                    cl = Thread
                    for_msg = 'thread'
                elif self.cfg['threading'] in {'process', 'processing'}:
                    cl = Process
                    for_msg = 'process'
                else:
                    raise ValueError('Wrong value for "threading" property: {}', self.cfg['threading'])
                t = cl(target=self._run)
                t.start()
                self._threads.append((t, int(time.time())))
                return 'start_parallel', 'Task started in new {}'.format(for_msg)
            else:
                self._run()
                return 'done', 'Task done'
        except Exception as e:
            return 'error', str(e)
