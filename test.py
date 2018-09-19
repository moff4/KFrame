#!/usr/bin/env python3

from kframe.base.parent import Parent
from kframe.plugins.stats import LOAD_SCHEME
import conf

p = Parent(conf)
p.add_plugin(key="stats",**LOAD_SCHEME)
p.init_plugins()
p.start()
p.stop()