#!/usr/bin/env python3

#
# # all you need is ...
# cp public.py private.py
# vim private.py
#
from .public import *
try:
	from .private import *
except Exception as e:
	pass

# filename for logs (str)
LOG_FILE 	=	"log.txt"

# how to show user time (str)
SHOW_TIME_FORMAT = "%d.%m.%Y %H:%M:%S"
