#!/usr/bin/env python3
import json

from kframe import Plugin


class PlannerCGI(Plugin):
    def init(self, **kwargs):
        defaults = {
            'only_local_hosts': True,
            'stat_url': '/{}-admin/planner/'.format(self.P.name)
        }
        self.cfg = {k: kwargs[k] if k in kwargs else defaults[k] for k in defaults}
        self.handlers = {
            'show_all': self.show_all,
            'show_single': self.show_single,
            'run': self.task_run,
            'update': self.task_update,
            'delete': self.task_delete,
        }

    # =========================================================================
    #                              HANDLERS
    # =========================================================================

    def show_all(self, req):
        req.resp.code = 200
        req.resp.data = json.dumps(
            {
                'result': self.P.planner.tasks
            }
        )

    def show_single(self, req):
        key = req.args.get('key')
        if key:
            task = self.P.planner.get_task(key)
            if task:
                res = {
                    'result': task,
                }
            else:
                res = {
                    'error': 'no such task',
                }
            req.resp.data = json.dumps(res)
            req.resp.code = 200
        else:
            req.resp.data = json.dumps({
                'error': 'param "key" must be passed',
            })
            req.resp.code = 400

    def task_run(self, req):
        """
            run task stored in planner
            return status, errmsg and logs
        """
        key = req.args.get('key')
        if not key:
            req.resp.data = json.dumps({
                'error': 'param "key" must be passed',
            })
            req.resp.code = 400
            return req.resp
        set_after = req.args.get('set_after', '0')
        set_after = int(set_after) if set_after.isdigit() else False
        self.P.log_store_set(True)
        status, errmsg = self.P.planner.run_task(key=key, set_after=set_after)
        logs = self.P.log_storage()
        self.P.log_store_set(False)
        self.Debug('task done; collected {} logs', len(logs))
        req.resp.data = json.dumps({
            'result': status,
            'errmsg': errmsg,
            'logs': logs,
        })
        req.resp.code = 200

    def task_update(self, req):
        """
            update or create new task
        """
        key = req.args.get('key')
        if not key:
            req.resp.data = json.dumps({
                'error': 'param "key" must be passed',
            })
            req.resp.code = 400
            return req.resp
        try:
            res = {
                'result': self.P.planner.update_task(key=key, **req.args)
            }
        except Exception as e:
            res = {
                'error': str(e),
            }
        finally:
            req.resp.data = json.dumps(res)
            req.resp.code = 200

    def task_delete(self, req):
        """
            delete task
        """
        key = req.args.get('key')
        if not key:
            req.resp.data = json.dumps({
                'error': 'param "key" must be passed',
            })
            req.resp.code = 400
            return req.resp
        else:
            self.P.planner.delete_task(key)
            req.resp.data = json.dumps({'result': True})
            req.resp.code = 200

    # =========================================================================
    #                                HOOK
    # =========================================================================

    def get(self, req):
        if req.url.startswith(self.cfg['stat_url']) and self.cfg['only_local_hosts'] and req.is_local():
            key = req.url[len(self.cfg['stat_url']):]
            if key in self.handlers:
                return self.handlers[key](req)
            else:
                from kframe.plugins.neon.utils import NOT_FOUND
                self.Debug('key is "{}"', key)
                return req.resp.set(
                    code=404,
                    data=NOT_FOUND,
                ).add_header('Content-Type', 'application/json')
        else:
            from kframe.plugins.neon.utils import NOT_FOUND
            if not req.url.startswith(self.cfg['stat_url']):
                self.Debug('url does not starts with "{}"', self.cfg['stat_url'])
            else:
                self.Debug('ip({}) is not local', req.ip)
            return req.resp.set(
                code=404,
                data=NOT_FOUND,
            ).add_header('Content-Type', 'application/json')
