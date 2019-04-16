#!/usr/bin/env python3
import json
import random

from kframe.plugins.xeon import WSHandler


class LoggerWSHandler(WSHandler):
    """
        WS handler for dumping logs
    """
    name = 'logger_ws_handler'

    Path = '/logger.ws'

    defaults = {
        'levels': None,
    }

    def init(self, **kwargs):
        self.key = '{}_{}'.format(self.name, random.randint(0, 10**5))
        super().init(**kwargs)

    def on_validate(self):
        self.P.logger.add_hook(
            target=self.log_hook,
            key=self.key,
            levels=self.cfg['levels'],
        )

    def on_end(self):
        self.P.logger.del_hook(self.key)

    def handle_incoming_msg(self, message):
        """
            Will be called on new incoming text message
            For example: Origin check
        """
        try:
            data = json.loads(message)
            if data.get('update'):
                self.cfg.update(data['update'])
            if 'levels' in data['update']:
                self.P.logger.upd_hook(
                    target=self.log_hook,
                    key=self.key,
                    levels=self.cfg['levels'],
                )
        except Exception:
            pass

    def log_hook(self, **kwargs):
        self.send_message(
            json.dumps(
                {
                    'method': 'logs',
                    'items': [
                        kwargs
                    ],
                }
            )
        )
