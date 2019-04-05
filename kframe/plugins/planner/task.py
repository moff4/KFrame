#!/usr/bin/env python3

import time


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
        self._convert_shedule(self.cfg)

    @staticmethod
    def _convert_shedule(cfg):
        if 'shedule' not in cfg:
            return
        bz = []
        for i in cfg['shedule']:
            if len(i) != 2:
                raise ValueError('invalid value of property "shedule"')
            az = []
            for j in i:
                r = 0
                for k in j.split(':'):
                    r = r * 60 + int(k)
                az.append(r)
            bz.append(tuple(az))
        cfg['shedule'] = bz

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
        if not kwargs and args and isinstance(args[0], dict):
            cfg = args[0]
        else:
            cfg = kwargs
        self._convert_shedule(cfg)
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
        return self.cfg.copy()

    def run(self):
        """
            run task
            (in this thread and this proccess)
        """
        return self.cfg['target'](
            *self.cfg['args'],
            **self.cfg['kwargs']
        )
