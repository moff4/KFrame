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
