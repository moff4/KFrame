#!/usr/bin/env python3

from abc import (
    abstractmethod,
    abstractproperty,
)


class AbstractStat:
    """
        Base class for all stats
    """
    stat_type = 'abstract'

    @abstractmethod
    def __init__(self, default=None, **kwargs):
        """
            Constructor
        """
        raise NotImplemented('abstract method "__init__"')

    @abstractmethod
    def add(self, value):
        """
            add value
        """
        raise NotImplemented('abstract method "add"')

    @abstractmethod
    def reset(self):
        """
            drop stat
        """
        raise NotImplemented('abstract method "reset"')

    @abstractproperty
    def value(self):
        """
            export value
        """
        raise NotImplemented('abstract method "value"')
