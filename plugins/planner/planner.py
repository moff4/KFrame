#!/usr/bin/env python3

import time
from threading import Thread
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
#         offset - int , def 0
#         args - list/tuple , def []
#         kwargs - dict , def {}
#         threading - bool , def False - run in new thread
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
        tasks = []
        for i in self.tasks:
            if all([
                self.tasks[i]['after'] is None or self.tasks[i]['after'] <= time.time(),
                self.tasks[i]['times'] is None or self.tasks[i]['times'] > 0
            ]):
                tasks.append((i, self.tasks[i]))
        if len(tasks) <= 0:
            return None, 10.0
        t = time.localtime()
        t = int((t.tm_hour * 60 + t.tm_min) * 60 + t.tm_sec)

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
            self.Debug(
                'LIMIT={}, RUNNING={}',
                self.tasks[key]['max_parallel_copies'],
                len(
                    filter(
                        lambda x: x[0] == key,
                        self._running_tasks
                    )
                )
            )
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
                    ) > self.tasks[key]['max_parallel_copies']:
                        t = Thread(target=self._do, args=[key])
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
