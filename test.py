#!/usr/bin/etc python3

import kframe as kf
import conf

p = kf.Parent(conf)
p.add_plugin(key="sql",target=kf.plugins.SQL,module=False,args=(conf.SQL,))
p.init_plugins()
p.start()
p.stop()