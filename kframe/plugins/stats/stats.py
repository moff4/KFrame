#!/usr/bin/env python3

from kframe.base.plugin import Plugin
from kframe.plugins.stats.type_stats import (
    StatInc,
    StatSum,
    StatAver,
    StatEvent,
    StatSingle,
    StatEventCounter,
)

STAT_TYPES = {
    'inc': StatInc,
    'single': StatSingle,
    'aver': StatAver,
    'sum': StatSum,
    'event': StatEvent,
    'event_counter': StatEventCounter,
}


class Stats(Plugin):
    def init(self):
        self._stats = {}

# ==========================================================================
#                                 USER API
# ==========================================================================

    def init_stat(self, key, type, rewrite=False, **kwargs):
        """
            initialize new stat
            params:
              <must be>
                key - (hashable) internal name of stat
                type - (str) type of stat possible: aver / collect / set / single / inc / sum / event / event-inc
              <optional>
                desc - str - description
                default - initial value
                count - number of elements saved for type "aver" and "collect"
                  default: 500
                increment - increment for signle call for type "inc"
                  default: 1
                limit - timeout for stats fot types event and event-inc
                  default: 3600
        """
        if type not in STAT_TYPES:
            raise ValueError('Unknown type of stat')
        if key in self._stats and not rewrite:
            return self
        self._stats[key] = STAT_TYPES[type](**kwargs)
        return self

    def add(self, key, value=None):
        """
            add stat data
            return True in case of success
            or False in case of error
        """
        if key not in self._stats:
            return False
        self._stats[key].add(value)
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
        return self._stats[key].value if key in self._stats else None

    def reset(self, key, value=None):
        """
            delete saved stat
        """
        if key in self._stats:
            self._stats[key].reset()
        return self

    def reset_all(self):
        """
            delete all saved stats
        """
        for key in self._stats:
            self._stats[key].reset()
        return self

    def export(self, extension=False):
        """
            extansion - flag to export more or less information
            extension - False => return dict : 'key' : value
            extension - True => return dict : 'key' : { 'desc' : description , 'data' : value, 'type': type }
            return dict containing all stats
        """
        return {
            key: {
                'desc': getattr(self._stats[key], 'desc', key),
                'data': self._stats[key].value,
                'type': self._stats[key].stat_type
            }
            for key in self._stats
        } if extension else {
            key: self._stats[key].value for key in self._stats
        }
