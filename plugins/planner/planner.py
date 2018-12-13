#!/usr/bin/env python3

import time
from threading import Thread

from kframe.base import Plugin

'''
task - dict = {
	MUST BE:
		key - str
		target - function
	OPTIONAL:
		hours - 0..23 , def 0
		min - 0..59 , def 0
		sec - 0..59 , def 0
		offset - int , def 0
		args - list/tuple , def []
		kwargs - dict , def {}
		threading - bool , def False
}
'''
class Planner(Plugin):
	def init(self, tasks=None):
		self._run = True
		self._m_thead = None
		self._threads = []
		self.tasks = []
		if not all(map(self.registrate, [] if tasks is None else tasks)):
			self.FATAL = True
			self.errmsg = "Some tasks badly configured"

	#
	# return ( next task as dict , delay as int )
	# 
	def next_task(self):
		if len(self.tasks) < 0:
			return None, 10.0
		t = time.localtime()
		t = int((t.tm_hour * 60 + t.tm_min) * 60 + t.tm_sec)
		return sorted([ (task,((task['hours'] * 60 + task['min']) * 60 + task['sec']) - ((t - task['offset']) % ((task['hours'] * 60 + task['min']) * 60 + task['sec']))) for task in self.tasks], key=lambda x:x[0])[0]

	#
	# pop dead threads
	#
	def check_threads(self):
		az = []
		for i in self._threads:
			if i.is_alive():
				az.append(i)
			else:
				i.join()
		self._threads = az

	#
	# run single task
	#
	def _do(self, task):
		try:
			_t = time.time()
			task['target'](*task['args'], **task['kwargs'])
			self.Debug('{key} done in {t} sec'.format(t='%.2f'%(time.time() - _t), **task))
		except Exception as e:
			self.Error("{key} - ex: {e}".format(e=e, **task))

	#
	# main loop
	#
	def _loop(self, loops=None):
		while self._run and (loops is None or loops > 0):
			task , delay = self.next_task()
			if delay > 5.0 or task is None:
				time.sleep(5.0)
			else:
				time.sleep(delay)
				if task['threading']:
					t = Thread(target=self._do, args=[task])
					t.start()
					self._threads.append(t)
				else:
					self._do(task)
				self.check_threads()
			if loops is not None and loops > 0:
				loops -= 1
		self.P.stop()

	#==========================================================================
	#                                  USER API
	#==========================================================================

	def registrate(self,**task):
		must = ['key', 'target']
		if any(map(lambda x:x not in task, must)):
			return False
		defaults = {
			'hours': 0,
			'min': 0,
			'sec': 0,
			'offset': 0,
			'args': [],
			'kwargs': {},
			'threading': False
		}
		self.tasks.append({key: task[key] if key in task else defaults[key] for key in (list(defaults.keys()) + must)})
		return True

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
