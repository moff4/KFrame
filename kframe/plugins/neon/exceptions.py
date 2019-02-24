#!/usr/bin/env python

from .utils import *


class ResponseError(Exception):
    def __init__(self, message=None, status=500, headers=None):
        super().__init__(message)
        self.status = status
        self.message = (SMTH_HAPPENED if status >= 500 else NOT_FOUND) if message is None else message
        self.headers = CONTENT_HTML if headers is None else headers
