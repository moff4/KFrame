#!/usr/bin/env python3

from kframe.plugins.xeon.base import BaseWSHandler


class WSHandler(BaseWSHandler):
    """
        Prototype of WS handler
        inherit and overwrite all handlers you need
    """
    name = 'ws_handler'

    Path = '/'

    def on_validate(self):
        """
            Will be called just after ws handshake
            Example: for cookie check / adding ws to pool
        """
        pass

    def on_request(self):
        """
            Will be called before ws handshake
            Example: for Origin check
        """
        pass

    def on_end(self):
        """
            Will be called after ws been closed
            Example: for deleteing from ws from pool
        """
        pass

    def handle_incoming_msg(self, message):
        """
            Will be called on new incoming text message
            For example: Origin check
        """
        pass

    def handle_incoming_bin(self, message):
        """
            Will be called on new incoming binary message
            For example: Origin check
        """
        pass

    def close(self):
        """
            Will be called when server is shutting down
            You should send message to close connection / reconnect
            if you are ready to close connection, call super().close()
            otherwise server will wait for client close connection
        """
        super().close()
