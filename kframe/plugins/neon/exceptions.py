#!/usr/bin/env python

from .utils import *


class ResponseError(Exception):
    """
        Exception to pass response to Neon server
    """

    def __init__(self, message=None, status=500, headers=None, cookies=None):
        """
            message - some data to be shown to user
            status - HTTP response code
            headers - dict of HTTP-headers
            cookies - list of dict:
                s - cookie boolean properties (like HttpOnly or Secure)
                kw - cookie key-value properies (like Max-Age or Domain)
                    (also cookie name and cookie value)
        """
        super().__init__(message)
        self.status = status
        self.message = (SMTH_HAPPENED if status >= 500 else NOT_FOUND) if message is None else message
        self.headers = CONTENT_HTML if headers is None else headers
        self.cookies = [] if cookies is None else cookies
