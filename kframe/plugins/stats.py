#!/usr/bin/env python3

from ..base.plugin import Plugin

POSSIBLE_TYPES = {'inc', 'single', 'aver', 'collect', 'set', 'sum'}
SIMPLE_TYPES = {'inc', 'single', 'collect', 'sum'}


class Stats(Plugin):
    def init(self):
        self._stats = {}

    def _export(self, key):
        if key not in self._stats:
            return None
        if self._stats[key]['type'] in SIMPLE_TYPES:
            return self._stats[key]['data']
        if self._stats[key]['type'] == 'aver':
            if len(self._stats[key]['data']) > 0:
                return '%.4f' % (sum(self._stats[key]['data']) / len(self._stats[key]['data']))
            return 0.0
        if self._stats[key]['type'] == 'set':
            return list(self._stats[key]['data'])

# ==========================================================================
#                                 USER API
# ==========================================================================

    def init_stat(self, key, type, rewrite=False, **kwargs):
        """
            initialize new stat
            params:
              <must be>
                key - (hashable) internal name of stat
                type - (str) type of stat possible: aver / collect / set / single / inc / sum
              <optional>
                desc - str - description
                default - initial value
                count - number of elements saved for type "aver" and "collect"
                  default: 500
                increment - increment for signle call for type "inc"
                  default: 1
        """
        if type not in POSSIBLE_TYPES:
            raise ValueError('Unknown type of stat')
        if key in self._stats and not rewrite:
            return self
        d = dict(kwargs)
        d['type'] = type
        if 'default' in d:
            default = d['default']
        else:
            if d['type'] == 'inc':
                default = 0
            elif d['type'] in {'aver', 'collect'}:
                default = []
            elif d['type'] == 'single':
                default = None
            elif d['type'] == sum:
                default = 0.0
            else:
                default = set()
        d['data'] = default
        self._stats[key] = d
        return self

    def add(self, key, value=None):
        """
            add stat data
            return True in case of success
            or False in case of error
        """
        if key not in self._stats:
            return False
        if self._stats[key]['type'] in {'aver', 'collect'}:
            count = self._stats[key]['count'] if 'count' in self._stats[key] else 500
            while len(self._stats[key]['data']) > count:
                self._stats[key]['data'].pop(0)
            self._stats[key]['data'].append(value)
        elif self._stats[key]['type'] == 'inc':
            self._stats[key]['data'] += self._stats[key]['increment'] if 'increment' in self._stats[key] else 1
        elif self._stats[key]['type'] == 'single':
            self._stats[key]['data'] = value
        elif self._stats[key]['type'] == 'set':
            self._stats[key]['data'].add(value)
        elif self._stats[key]['type'] == 'sum':
            self._stats[key]['data'] += value
        else:
            return False
        return True

    def init_and_add(self, key, type, value=None, **kwargs):
        """
            add stat data
            if stat is not initialized => init it!
        """
        self.init_stat(
            key=key,
            type=type,
            rewrite=False,
            **kwargs
        ).add(
            key=key,
            value=value
        )
        return self

    def get(self, key):
        """
        return saved data or None in case of error
        """
        return self._stats[key]['data'] if key in self._stats else None

    def export(self, extension=False):
        """
            extansion - flag to export more or less information
            extension - False => return dict : 'key' : value
            extension - True => return dict : 'key' : { 'desc' : description , 'data' : value, 'type': type }
            return dict containing all stats
        """
        return {
            key: {
                'desc': self._stats[key].get('desc', key),
                'data': self._export(key),
                'type': self._stats[key]['type']
            }
            for key in self._stats
        } if extension else {
            key: self._export(key) for key in self._stats
        }
