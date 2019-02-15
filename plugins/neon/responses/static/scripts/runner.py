#!/usr/bin/env python3

from ......base import Plugin


class ScriptRunner(Plugin):
    def init(self, text):
        self.text = text if isinstance(text, str) else text.decode()
        self.scripts_info = [
            ('<!--#@', '#@-->', self._run_1_0),
            ('<!--#', '#-->', self._run_1_1),
        ]

    def _run_1_1(self, text, args):
        text = '\n'.join(
            map(
                lambda x: x.strip(),
                filter(
                    lambda x: len(x) > 0 and not x.isspace(),
                    text.split('\n'),
                ),
            )
        )
        try:
            return str(eval(text, args, {}))
        except Exception as e:
            self.Error('Unexpectedly got: {}', e)
            self.Trace('Unexpectedly got:', _type='debug')

    def _run_1_0(self, text, args):
        text = '\n'.join(filter(lambda x: len(x) > 0 and not x.isspace(), text.split('\n')))
        local = {'result': ''}
        try:
            exec(text, args, local)
            return str(local['result'])
        except Exception as e:
            self.Error('Unexpectedly got: {}', e)
            self.Trace('Unexpectedly got:', _type='debug')

    def run(self, args):
        text = self.text
        k = 0
        for sci in self.scripts_info:
            while sci[0] in text and sci[1] in text:
                i = text.index(sci[0])
                j = text.index(sci[1])
                pt1 = text[:i]
                pt2 = text[j + len(sci[1]):]
                script = text[i + len(sci[0]):j]
                result = sci[2](script, args)
                if result is None:
                    self.Error(
                        'script №{} ({}{}) failed'.format(
                            k,
                            script[:15],
                            '...' if len(script) >= 25 else ''
                        )
                    )
                    return False
                text = pt1 + result + pt2
                k += 1
        self.text = text
        return True

    def export(self):
        return self.text
