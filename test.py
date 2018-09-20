#!/usr/bin/env python3

from kframe.base.parent import Parent
from kframe.plugins.web import Web
p = Parent()
p.add_plugin(key="web", target=Web, kwargs={'site_directory':'.'})
p.init_plugins()
p.start()
# open in your browser http://127.0.0.1:8080/test.py
p.stop()
# Ctr-C to stop