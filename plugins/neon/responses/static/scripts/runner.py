#!/usr/bin/env python3

from traceback import format_exc as Trace
from ......base import Plugin


class ScriptRunner(Plugin):
    def init(self, text):
        self.text = text if isinstance(text, str) else text.decode()
        self.scripts_info = [
            ('<!--#@', '#@-->', self._run_1_0),
        ]

    def _run_1_0(self, text, args):
        text = '\n'.join(filter(lambda x: len(x) > 0 and not x.isspace(), text.split('\n')))
        local = {'result': ''}
        try:
            exec(text, args, local)
            return str(local['result'])
        except Exception as e:
            self.Error('Unexpectedly got: {}', e)
            self.Debug('Unexpectedly got: {}', Trace())

    def run(self, args):
        text = self.text
        k = 0
        for sci in self.scripts_info:
            while sci[0] in text and sci[1] in text:
                i = text.index(sci[0])
                j = text.index(sci[1])
                pt1 = text[:i]
                pt2 = text[j + len(sci[1]):]
                result = sci[2](text[i + len(sci[0]):j], args)
                if result is None:
                    raise RuntimeError('script #{} failed', k)
                text = pt1 + result + pt2
                k += 1
        self.text = text

    def export(self):
        return self.text
