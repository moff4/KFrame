#!/usr/bin/env python3

from kframe.plugins.stats.type_stats.base_stat import AbstractStat


class StatInc(AbstractStat):
    """
        Counter, only increment value
    """

    stat_type = 'inc'

    def __init__(self, default=0, **kwargs):
        """
            Constructor
        """
        self._value = default
        self._increment = kwargs.get('increment', 1)
        if 'desc' in kwargs:
            self.desc = kwargs['desc']

    def add(self, value=None):
        """
            add value
        """
        self._value += self._increment

    def reset(self):
        """
            drop stat
        """
        self._value = 0

    @property
    def value(self):
        """
            export value
        """
        return self._value
