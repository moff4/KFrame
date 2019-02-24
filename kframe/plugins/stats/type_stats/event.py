#!/usr/bin/env python3
import time
from collections import deque

from kframe.plugins.stats.type_stats.base_stat import AbstractStat


class StatEvent(AbstractStat):
    """
        event aggregator
    """

    stat_type = 'event'

    def __init__(self, default=None, **kwargs):
        """
            Constructor
        """
        self._value = deque()
        self._limit = kwargs.get('limit', 3600)
        if 'desc' in kwargs:
            self.desc = kwargs['desc']

    def _clean(self, t):
        while len(self._value) > 0 and (t - self._value[0][0]) > self._limit:
            self._stamps.popleft()

    def add(self, value):
        """
            add event
        """
        t = time.time()
        self._clean(t)
        self._value.append((t, value))

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
        return list(self._value)
