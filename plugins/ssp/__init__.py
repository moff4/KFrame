#!/usr/bin/env python3

from .ssp import SSP 

DEFAULT_LOAD_SCHEME = {
	"target":SSP,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[],
	"autostart":False
}