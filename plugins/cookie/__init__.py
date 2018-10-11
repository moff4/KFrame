#!/usr/bin/env python3

from .cookie import Cookie
from .cookies import Cookies

DEFAULT_LOAD_SCHEME = {
	'target':Cookies,
	'module':True,
	'args':(),
	'kwargs':{},
	'depends':[],
	'autostart':False
}