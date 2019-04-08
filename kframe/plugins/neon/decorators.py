#!/usr/bin/env python3

from kframe.plugins.neon.exceptions import ResponseError
from kframe.modules.jscheme import apply


def autocheck(scheme):
    """
        decator for checking incoming params
    """
    def _f(func):
        def _g(req, *args, **kwargs):
            try:
                req.args = apply(req.args, scheme)
            except Exception as e:
                raise ResponseError(
                    code=400,
                    message='Bad format',
                )
            func(req, *args, **kwargs)
        return _g
    return _f


class recursion(object):
    """
        optimizations in recursive calling
        use as decorator
    """

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        result = self.func(*args, **kwargs)
        while callable(result):
            result = result()
        return result

    def call(self, *args, **kwargs):
        return lambda: self.func(*args, **kwargs)
