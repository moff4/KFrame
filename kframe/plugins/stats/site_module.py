#!/usr/bin/env python3
import json

from kframe import Plugin
from kframe.plugins.neon.utils import NOT_FOUND


class StatsCGI(Plugin):
    def init(self, **kwargs):
        defaults = {
            'only_local_hosts': True,
            'stat_url': '/{}-admin/stats'.format(self.P.name)
        }
        self.cfg = {k: kwargs[k] if k in kwargs else defaults[k] for k in defaults}

    def get(self, req):
        if req.url == self.cfg['stat_url'] and self.cfg['only_local_hosts'] and req.is_local():
            return req.resp.set(
                code=200,
                data=json.dumps(
                    self.P.stats.export(
                        extension=req.args.get('ext', None) == '1'
                    )
                )
            ).add_header('Content-Type', 'application/json')
        else:
            return req.resp.set(
                code=404,
                data=NOT_FOUND,
            ).add_header('Content-Type', 'application/json')
