#!/usr/bin/env python3

import time
import json
from threading import Thread

from ..base.plugin import Plugin


class Cache(Plugin):
    """
        kwargs:
          timeout - interval of checking nodes for old rows ; default: 1.0
          save_file - filename for temporary buffer ; default: cache.json
          autosave - save cached data to <save_file> every <timeout>
    """

    def init(self, **kwargs):
        defaults = {
            'timeout': 1.0,
            'save_file': 'cache.json',
            'autosave': False,
        }
        self.cfg = {i: kwargs[i] if i in kwargs else defaults[i] for i in defaults}
        """
            nodename -> [
              cache as dict,
              timeout as float,
              filter as function : time.time() of add -> bool,
              autoclean
            ]
        """
        self._d = {}
        self._th = None
        self._run = True
        self.load()
# ==========================================================================
#                                 UTILS
# ==========================================================================

    def save(self):
        try:
            data = {}
            for i in self._d:
                data[i] = {
                    'd': self._d[i][0],
                    't': self._d[i][1],
                    'a': self._d[i][3],
                }
            with open(self.cfg['save_file'], 'w') as f:
                f.write(json.dumps(data))
        except Exception as e:
            self.Warning('save temporary file: {}', e)

    def load(self):
        try:
            data = json.load(open(self.cfg['save_file']))
            for i in data:
                self._d[i] = [data[i]["d"], data[i]["t"], None, data[i]["a"]]
        except Exception as e:
            self.Warning('read temporary file: {}', e)

    def _clean(self):
        k = 0
        for nodename in self._d:
            if self._d[nodename][3]:
                k += self.clean_node(nodename)
        if k > 0:
            self.Debug('clean: delete {} rows', k)

    def _loop(self):
        self.Debug("start loop")
        while self._run:
            time.sleep(self.cfg['timeout'])
            self._clean()
            if self.cfg['autosave']:
                self.save()
        self.Debug("stop loop")

# ==========================================================================
#                                USER API
# ==========================================================================

    def start(self):
        self._run = True
        self._th = Thread(target=self._loop)
        self._th.start()

    def stop(self, wait=True):
        self._run = False
        if wait:
            self._th.join()
            self.save()

    def add_node(self, nodename, timeout=3600, _filter=None, autoclean=True):
        """
            Add new node or change timeout if node exists
            Timeout will be ignored if _filter passed
            filter is fuction : value , timestamp => bool
              value - smth saved
              timestamp - timestamp when this was added
              return True if row must be deleted
        """
        if nodename not in self._d:
            self._d[nodename] = [{}, timeout, _filter, autoclean]
        else:
            self._d[nodename] = [self._d[nodename][0], timeout, _filter, autoclean]

    def delete_node(self, nodename):
        """
            Delete whole node
        """
        if nodename in self._d:
            self._d.pop(nodename)

    def clean_node(self, nodename):
        """
            delete old rows from node
            return number of deleted rows
        """
        if nodename not in self._d:
            return 0
        k = 0
        _time = time.time()
        for key in list(self._d[nodename][0].keys()):
            if self._d[nodename][2] is None:
                if (self._d[nodename][1] + self._d[nodename][0][key][1]) < _time:
                    self._d[nodename][0].pop(key)
                    k += 1
            elif self._d[nodename][2](*self._d[nodename][0][key][1]):
                self._d[nodename][0].pop(key)
                k += 1
        return k

    def push(self, nodename, key, val):
        """
            Push new data to cache
        """
        self._d[nodename][0][key] = (val, time.time())

    def get(self, nodename, key):
        """
            Return value for key in cache or None
        """
        if key in self._d[nodename][0]:
            return self._d[nodename][0][key][0]
        else:
            return None

    def count(self, nodename):
        """
            return number of keys in one node
             OR return 0
        """
        if nodename in self._d:
            return len(self._d[nodename][0])
        else:
            return 0
