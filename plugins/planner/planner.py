#!/usr/bin/env python3

import time
from threading import Thread
from multiprocessing import Process
from traceback import format_exc as Trace
from kframe.base import Plugin


#
# task - dict = {
#     MUST BE:
#         key - str
#         target - function
#     OPTIONAL:
#         hours - int , def 0
#         min - int , def 0
#         sec - int , def 0
#         shedule - list of tuples ('HH:MM:SS' str, 'HH:MM:SS' str), def ('00:00:00','23:59:59') - shedule (from, to)
#         calendar - { 'allowed' or 'disallowed': { month as key [1..12] => set of days [1..31] }}
#           def {} (allowed always) - match days, when it's allowed or disallowed to run function
#         offset - int , def 0
#         args - list/tuple , def []
#         kwargs - dict , def {}
#         threading - bool or str , def False - no threadign; True - run in new thread; 'process' - run in new process;
#         after - int , def None - do not run before this unix timestamp
#         times - int , def None - number of runs
#         max_parallel_copies - int , def None - allowed number of parallel tasks run (None - no restrictions)
# }
#
class Planner(Plugin):
    def init(self, tasks=None):
        self._run = True
        self._m_thead = None
        self._threads = []
        self._running_tasks = []  # [ .. ,( key, thread), ..]
        self.tasks = {}
        self._last_task = None
        if not all([self.registrate(**task) for task in ([] if tasks is None else tasks)]):
            self.FATAL = True
            self.errmsg = "Some tasks badly configured"

    #
    # return ( key , delay as int )
    #
    def next_task(self):
        def calendar(t, allowed=None, disallowed=None):
            def in_cal(t, cal):
                return t.tm_mon in cal and t.tm_mday in cal[t.tm_mon]
            if allowed is None and disallowed is None:
                return True
            elif allowed is None or disallowed is None:
                if disallowed is not None and in_cal(t, disallowed):
                    return False
                elif allowed is not None and in_cal(t, allowed):
                    return True
            else:
                raise ValueError('expected only "allowed" or "disallowed" in calendar property, not both of them')

        def shedule(t, shed):
            return any(
                map(
                    lambda x: x[0] <= t <= x[1],
                    shed,
                )
            )

        tasks = []
        _t = time.localtime()
        t = int((_t.tm_hour * 60 + _t.tm_min) * 60 + _t.tm_sec)
        for i in self.tasks:
            if all([
                self.tasks[i]['after'] is None or self.tasks[i]['after'] <= time.time(),
                self.tasks[i]['times'] is None or self.tasks[i]['times'] > 0,
                calendar(_t, **self.tasks[i]['calendar']),
                shedule(t, self.tasks[i]['shedule']),
            ]):
                tasks.append((i, self.tasks[i]))
        if len(tasks) <= 0:
            return None, 10.0

        az = []  # key , sec left
        for key, task in tasks:
            _t = (task['hours'] * 60 + task['min']) * 60 + task['sec']
            _t = _t - ((t - task['offset']) % (_t))
            az.append((key, _t))
        if self.P.get_param('--debug-planner', False):
            for key, delay in az:
                self.Debug('shedule: next {key} in {delay} sec', key=key, delay=delay)
        return sorted(az, key=lambda x: x[1])[0]

    #
    # pop dead threads
    #
    def check_threads(self):
        az = []
        for i in self._running_tasks:
            if i[1].is_alive():
                az.append(i)
            else:
                i[1].join()
        self._running_tasks = az

    #
    # run single task
    #
    def _do(self, key):
        self.Debug('Start {}', key)
        try:
            _t = time.time()
            run_id = "{}^@^{}".format(key, int(_t))
            if self._last_task != run_id:
                self._last_task = run_id
                if self.tasks[key]['times'] is not None:
                    self.tasks[key]['times'] -= 1
                self.tasks[key]['target'](*self.tasks[key]['args'], **self.tasks[key]['kwargs'])
                self.Debug('{key} done in {t} sec'.format(t='%.2f' % (time.time() - _t), key=key))
        except Exception as e:
            self.Debug("{} - ex: {}".format(key, Trace()))
            self.Error("{} - ex: {}".format(key, e))

    #
    # main loop
    #
    def _loop(self, loops=None):
        while self._run and (loops is None or loops > 0):
            key, delay = self.next_task()
            if self.P.get_param('--debug-planner', False):
                self.Debug('next {key} in {delay} sec', key=key, delay=delay)
            if delay > 5.0 or key is None:
                time.sleep(5.0)
            else:
                time.sleep(delay)
                if self.tasks[key]['threading']:
                    if self.tasks[key]['max_parallel_copies'] is None or len(
                        list(filter(lambda x: x[0] == key, self._running_tasks))
                    ) < self.tasks[key]['max_parallel_copies']:
                        if self.tasks[key]['threading'] in {'thread', 'threading', True}:
                            cl = Thread
                        elif self.tasks[key]['threading'] in {'process', 'processing'}:
                            cl = Process
                        else:
                            raise ValueError('Wrong value for "threading" property: {}', self.tasks[key]['threading'])
                        t = cl(target=self._do, args=[key])
                        t.start()
                        self._running_tasks.append((key, t))
                    else:
                        self.Notify('too many running copies of task "{key}"', key=key)
                else:
                    self._do(key)
                self.check_threads()
            if loops is not None and loops > 0:
                loops -= 1
        self.P.stop()

# ==========================================================================
#                                  USER API
# ==========================================================================

    def registrate(self, key, target, **task):
        if key in self.tasks:
            return False
        defaults = {
            'hours': 0,
            'min': 0,
            'sec': 0,
            'offset': 0,
            'shedule': [('00:00:00', '23:59:59')],
            'calendar': {},
            'args': [],
            'kwargs': {},
            'threading': False,
            'after': None,
            'times': None,
            'max_parallel_copies': None,
        }
        task['key'] = key
        task['target'] = target
        self.tasks[key] = {
            key: task[key] if key in task else defaults[key]
            for key in (
                list(defaults.keys()) + ['key', 'target']
            )
        }
        bz = []
        for i in self.tasks[key]['shedule']:
            if len(i) != 2:
                raise ValueError('invalid value of property "shedule"')
            az = []
            for j in i:
                r = 0
                for k in j.split(':'):
                    r = r * 60 + int(k)
                az.append(r)
            bz.append(tuple(az))
        self.tasks[key]['shedule'] = bz
        return True

    def update_task(self, key, **task):
        if key in self.tasks:
            self.tasks[key].update(task)
            return True
        return self.registrate(key=key, **task)

    def delete_task(self, key):
        if key in self.tasks:
            self.tasks.pop(key)

    def start(self):
        self._run = True
        self._m_thead = Thread(target=self._loop)
        self._m_thead.start()
        return self

    def stop(self, wait=True):
        self._run = False
        if wait and self._m_thead is not None:
            for i in self._threads:
                i.join()
            self._m_thead.join()
