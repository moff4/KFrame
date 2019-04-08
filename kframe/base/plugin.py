#!/usr/bin/env python3

from traceback import format_exc

from kframe.base.utils import copy_n_update


class Plugin:
    """
        Base class for all plugins
    """

    name = 'raw_plugin'

    defaults = {}

    def __init__(self, parent, plugin_name, args, kwargs):
        try:
            self.P = parent
            self.name = plugin_name

            self._params = {}

            self.FATAL = False
            self.errmsg = 'initialized successfully - {}'.format(self.name)

            self._force_log = self.P.get_param(
                '--{}--debug'.format(
                    self.name,
                ),
                False,
            )
            self.cfg = {
                k:
                copy_n_update(self.defaults[k], kwargs.get(k, {}))
                if isinstance(self.defaults[k], dict) else
                kwargs.get(k, self.defaults[k])
                for k in self.defaults
            }

            argv = self.P.get_params()
            prefix = '--{}-'.format(self.name)
            kwargs.update({
                '_'.join(k[len(prefix):].split('-')): int(argv[k])
                if isinstance(argv[k], str) and argv[k].isdigit() else
                argv[k]
                for k in filter(
                    lambda x: x.startswith(prefix) and x != prefix,
                    argv,
                )
            })

            try:
                self.init(*args, **kwargs)
            except Exception as e:
                self.Trace('__init__ - init : ', _type='error')
                raise

        except Exception as e:
            self.FATAL = True
            self.errmsg = '%s: %s' % (self.name, e)

    def get_argv_rules(self):
        """
            export argv rules for Parent
        """
        return self._params


# ==========================================================================
#                            USER API
# ==========================================================================
    def init(self):
        """
            CAN BE OVERLOADED
            constructor, will be called from __init__()
        """
        pass

    def Trace(self, st, *args, **kwargs):
        """
            save Traceback
        """
        self(
            st='{}\n{}'.format(
                st.format(*args, **kwargs),
                format_exc()
            ),
            _type=kwargs['_type'] if '_type' in kwargs else 'debug'
        )

    def Debug(self, st, *args, **kwargs):
        """
            debug log function
        """
        self(st=st.format(*args, **kwargs), _type='debug')

    def Error(self, st, *args, **kwargs):
        """
            error log function
        """
        self(st=st.format(*args, **kwargs), _type='error')

    def Warning(self, st, *args, **kwargs):
        """
            debug log function
        """
        self(st=st.format(*args, **kwargs), _type='warning')

    def Notify(self, st, *args, **kwargs):
        """
            debug log function
        """
        self(st=st.format(*args, **kwargs), _type='info')

    def log(self, st='', _type='info'):
        """
            local log function
        """
        self.P.log(
            '{}: {}'.format(self.name, st),
            _type=_type,
            force=self._force_log,
            plugin_name=self.name,
        )

    def __call__(self, st='', _type='info'):
        """
            local log function
        """
        self.log(st=st, _type=_type)

    def __getitem__(self, key):
        """
            operator overload
            return already initialized plugin or module
            or return None
        """
        return self.P.get_plugin(key)

    def __contains__(self, key):
        """
            operator overload
            return True if plugin or module exists
            or False if not
        """
        return key in self.P

    def get_param(self, key, default=None):
        """
            return param's value if param was passed
            return True as bool if that's was flag
            else return None if nothing was passed
        """
        return self.P.get_param(key=key, default=default)

    def start(self):
        """
            CAN BE OVERLOADED
            method to start your main job
        """
        pass

    def stop(self, wait=True):
        """
            CAN BE OVERLOADED
            method to stop your main job
        """
        pass

    def expect_argv(self, key, critical=False, description=""):
        """
            add expected key to storage
            flag as bool - True if we expect flag or False if param
            critical as bool - True if this param/flag is critical (default: False)
            description as str - some descrition for human (default: "")
        """
        self._params[key] = {
            'critical': critical,
            'description': description,
        }
