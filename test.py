#!/usr/bin/env python3

from kframe.base.parent import Parent
from kframe.plugins.cookie import Cookies
import conf

p = Parent(conf)
p.add_plugin(key="sql",target=Cookies,module=True,args=())
p.init_plugins()
p.start()
p.stop()