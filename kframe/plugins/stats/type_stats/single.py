#!/usr/bin/env python3

from kframe.plugins.stats.type_stats.inc import StatInc


class StatSingle(StatInc):
    """
        Sum aggegator
    """

    stat_type = 'single'

    def add(self, value):
        """
            add value
        """
        self._value = value
