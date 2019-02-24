#!/usr/bin/env python3

from kframe.plugins.stats.type_stats.inc import StatInc


class StatSum(StatInc):
    """
        Sum aggegator
    """

    stat_type = 'sum'

    def add(self, value):
        """
            add value
        """
        self._value += value
