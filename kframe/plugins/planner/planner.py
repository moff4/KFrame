#!/usr/bin/env python3

import time
from threading import Thread

from kframe.base import Plugin
from kframe.plugins.stats import Stats
from kframe.plugins.planner.site_module import PlannerCGI
from kframe.plugins.planner.task import Task


class Planner(Plugin):
    """
        tasks - list of tasks
        task - dict = {
            MUST BE:
                key - str
                target - function
            OPTIONAL:
                hours - int , def 0
                min - int , def 0
                sec - int , def 0
                shedule - list of tuples ('HH:MM:SS' str, 'HH:MM:SS' str), def ('00:00:00','23:59:59')
                     - shedule (from, to)
                calendar - { 'allowed' or 'disallowed': { month as key [1..12] => set of days [1..31] }}
                  def {} (allowed always) - match days, when it's allowed or disallowed to run function
                weekdays - {0,..,6} - set/list of weekdays when it's allowed to run function (Monday is 0, Sunday is 6)
                offset - int , def 0
                args - list/tuple , def []
                kwargs - dict , def {}
                threading - bool or str , def False - no threadign; True - run in new thread; 'process'
                     - run in new process;
                after - int , def None - do not run before this unix timestamp
                times - int , def None - number of runs
                max_parallel_copies - int , def None - allowed number of parallel tasks run (None - no restrictions)
                enable - bool, def True - if False, task will not be run
        }
    """

    name = 'planner'
    defaults = {
        'enable_stats': False,
        'add_neon_handler': False,
        'neon_handler_cfg': {}
    }

    def init(self, tasks=None, **kwargs):
        self._run = True
        self._m_thead = None
        self._threads = []
        self._tasks = {}
        self._last_task = None
        self._shedule = []  # [ .., (key , sec left), ..]
        if not all([self.registrate(**task) for task in ([] if tasks is None else tasks)]):
            self.FATAL = True
            self.errmsg = "Some tasks badly configured"
            return
        self.P.fast_init(
            target=PlannerCGI,
            export=False,
            **self.cfg['neon_handler_cfg']
        )
        if self.cfg['enable_stats']:
            if 'stats' not in self:
                self.P.fast_init(target=Stats, export=False)
            self.P.stats.init_stat(
                key='planner-next-task',
                type='single',
                desc='Следующая задача',
            )
            self.P.stats.init_stat(
                key='planner-shedule',
                type='single',
                desc='Расписание задач',
            )
            self.P.stats.init_stat(
                key='planner-done-task',
                type='event',
                desc='Факты выполнения задач',
            )

    def next_task(self):
        """
            return ( key , delay as int )
        """

        _t = time.localtime()
        t = int((_t.tm_hour * 60 + _t.tm_min) * 60 + _t.tm_sec)
        az = [(i, self._tasks[i].seconds_left(t)) for i in self._tasks if self._tasks[i].ready_for_run(t=t, tm=_t)]
        if not az:
            return None, 10.0

        self._shedule = sorted(az, key=lambda x: x[1])
        if self.P.get_param('--debug-planner', False):
            for key, delay in self._shedule:
                self.Debug('shedule: next {key} in {delay} sec', key=key, delay=delay)
        if self.cfg['enable_stats']:
            self.P.stats.add('planner-next-task', '{} in {} sec'.format(*self._shedule[0]))
            self.P.stats.add(
                'planner-shedule',
                '\n'.join([
                    '{} in {}'.format(key, delay)
                    for key, delay in self._shedule
                ])
            )
        return self._shedule[0]

    def check_threads(self):
        """
            pop dead threads
        """
        for key in self._tasks:
            self._tasks[key].check_threads()

    def _loop(self, loops=None):
        """
            main loop
        """
        while self._run and (loops is None or loops > 0):
            key, delay = self.next_task()
            if self.P.get_param('--debug-planner', False):
                self.Debug('next {key} in {delay} sec', key=key, delay=delay)
            if delay > 5.0 or key is None:
                time.sleep(5.0)
            else:
                time.sleep(delay)
                code, msg = self._tasks[key].run()
                if code == 'error':
                    self.Error('task "{}" run: {}', key, msg)
                elif code is not None:
                    self.Debug('task "{}" run: {}', key, msg)
                self.check_threads()
            if loops is not None and loops > 0:
                loops -= 1
        self.P.stop()

# ==========================================================================
#                                  USER API
# ==========================================================================

    def registrate(self, key, target, **task):
        """
            return True in case of success
            -- possible raise Exception if params are of invalid type
        """
        if key in self._tasks:
            return False
        try:
            self._tasks[key] = Task(key=key, target=target, **task)
            return True
        except Exception as e:
            self.Error('registrate new task: {}', e)
            return False

    @property
    def tasks(self):
        """
            return tasks as dict
        """
        return {k: self._tasks[k].to_dict() for k in self._tasks}

    def get_task(self, key):
        """
            get task properties
        """
        return self._tasks[key].to_dict() if key in self._tasks else None

    def update_task(self, key, **task):
        """
            update task properties
        """
        if key in self._tasks:
            self._tasks[key].update(task)
            return True
        return self.registrate(key=key, **task) if 'target' in task else False

    def run_task(self, key, set_after=False):
        """
            run task
            return tuple(flag of success as bool, errmsg as str)
        """
        if key not in self._tasks:
            return False, 'Has no task "{}"'.format(key)
        else:
            code, msg = self._tasks[key].run(unplanned=True)
            if set_after and code in {'start_parallel', 'done'}:
                self._tasks[key].after = next(
                    filter(
                        lambda x: x[0] == key,
                        self._shedule
                    )
                )[0] + int(time.time())
            return code in {'start_parallel', 'done'}, msg

    def delete_task(self, key):
        """
            delete task
        """
        self._tasks.pop(key, None)

    def get_running_tasks(self):
        """
            return list of dict {
                key - str - key of task
                starttime - int - timestamp of start
            } or empty list if there are no running tasks
        """
        return [
            {
                'key': key,
                'starttime': i,
            }
            for key in self._tasks
            for i in self._tasks[key].get_running_tasks()
        ]

    def get_shedule(self):
        """
            return list of dict {
                key - str - key of task
                delay - int - seconds left before start
                starttime - int - timestamp of start
            } or empty list if there are no tasks
        """
        t = int(time.time())
        return [
            {
                'key': i[0],
                'delay': i[1],
                'starttime': t + i[1],
            }
            for i in self._shedule
        ]

    def get_next_task(self):
        """
            return dict {
                key - str - key of task
                delay - int - seconds left before start
                starttime - int - timestamp of start
            } or None if there are no tasks
        """
        if self._shedule:
            t = int(time.time())
            return {
                'key': self._shedule[0][0],
                'delay': self._shedule[0][1],
                'starttime': t + self._shedule[0][1],
            }

    def start(self):
        if self.cfg['add_neon_handler']:
            if 'neon' not in self:
                raise ValueError('for neon-handler Neon must be already initialized')
            else:
                self.P.neon.add_site_module(
                    module=self.P.planner_cgi,
                    path=self.P.planner_cgi.cfg['stat_url'],
                )

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
