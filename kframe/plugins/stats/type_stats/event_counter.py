#!/usr/bin/env python3
import time
from collections import (
    deque,
    Counter,
)

from kframe.plugins.stats.type_stats.base_stat import AbstractStat


class StatEventCounter(AbstractStat):
    """
        event counter
    """

    stat_type = 'event_counter'

    def __init__(self, default=None, **kwargs):
        """
            Constructor
        """
        self._value = Counter()
        self._stamps = deque()
        self._limit = kwargs.get('limit', 3600)
        if 'desc' in kwargs:
            self.desc = kwargs['desc']

    def _clean(self, t):
        while len(self._stamps) > 0 and (t - self._stamps[0]) > self._limit:
            self._value.pop(self._stamps.popleft(), None)

    def add(self, value=None):
        """
            add event
        """
        t = int(time.time())
        self._clean(t)
        self._value[t] += 1 if value is None else value
        self._stamps.append(t)

    def reset(self):
        """
            drop stat
        """
        self._value = Counter()
        self._stamps = deque()

    @property
    def value(self):
        """
            export value
        """
        return dict(self._value)
