#!/usr/bin/env python3

from kframe.plugins.neon.exceptions import ResponseError
from kframe.modules.jscheme import apply


def autocheck(scheme, method=False, post=False, data_decoder=None):
    """
        decator for checking incoming params
        method must be True for decorating methods
        post - for checking data in post
        data_decoder - function req.data (bytes by default) -> dict
            if data_decoder is None, req.data will be passed to Jscheme as it is
        result will be assigned to req.args
    """
    def _f(func):
        def _g(*args, **kwargs):
            try:
                req = args[int(method)]
                data = (req.data if data_decoder is None else data_decoder(req.data)) if post else req.args
                req.args = apply(data, scheme)
            except ValueError as e:
                req.Warning('CheckScheme: {}', e)
                raise ResponseError(
                    status=400,
                    message='Bad format',
                )
            func(*args, **kwargs)
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
