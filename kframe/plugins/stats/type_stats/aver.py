#!/usr/bin/env python3

from collections import deque

from kframe.plugins.stats.type_stats.base_stat import AbstractStat


class StatAver(AbstractStat):
    """
        Average aggegator
    """

    stat_type = 'aver'

    def __init__(self, default=None, **kwargs):
        """
            Constructor
        """
        self._value = deque()
        self._limit = kwargs.get('limit', 500)
        if 'desc' in kwargs:
            self.desc = kwargs['desc']

    def _clean(self):
        while len(self._value) > self._limit:
            self._value.popleft()

    def add(self, value):
        """
            add value
        """
        self._clean()
        self._value.append(value)

    def reset(self):
        """
            drop stat
        """
        self._value = deque()

    @property
    def value(self):
        """
            export value
        """
        return (sum(self._value) / len(self._value)) if len(self._value) > 0 else None
