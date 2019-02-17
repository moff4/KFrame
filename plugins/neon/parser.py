#!/usr/bin/env python3
import sys
from .utils import *

if sys.platform == 'win32':
    from socket import MSG_PEEK
    PEEK_FLAGS = MSG_PEEK
else:
    from socket import MSG_PEEK, MSG_DONTWAIT
    PEEK_FLAGS = MSG_PEEK | MSG_DONTWAIT


def parse_data(conn, cfg):
    """
        take socket and cfg and parse HTTP headers
        return dict of attributes/headers/url/args
    """
    request = {
        'url': b'',
        'args': {},
        'method': b'',
        'http_version': b'',
        'headers': {},
        'data': b'',
        'postfix': b''
    }
    st = readln(conn, max_len=cfg['max_header_length'])
    while 0 < len(st) and st[:1] != b' ':
        request['method'] += st[:1]
        st = st[1:]
    st = st[1:]
    while 0 < len(st) and st[:1] not in {b' ', b'?', b'#'}:
        request['url'] += st[:1]
        st = st[1:]
    request['url'] = urldecode(request['url'])
    if st[:1] == b'?':
        while (st[:1] != b' ') and len(st) > 0:
            st = st[1:]
            key = b''
            val = b''
            while 0 < len(st) and st[:1] != b'=':
                key += st[:1]
                st = st[1:]
            st = st[1:]
            while 0 < len(st) and st[:1] != b' ' and st[:1] != b'&':
                val += st[:1]
                st = st[1:]
            request['args'][key.decode('utf-8')] = urldecode(val)
    if st[:1] == b'#':
        st = st[1:]
        val = b''
        while st[:1] != b' ':
            val += st[:1]
            st = st[1:]
        request['postfix'] = val
    st = st[1:]
    while 0 < len(st) and st[:1] != b' ':
        request['http_version'] += st[:1]
        st = st[1:]

    while True:
        value = ''
        st = readln(conn, max_len=cfg['max_header_length']).decode('utf-8')
        if st == '':
            break
        else:
            st = st.split(':')
        key = st[0]
        for i in st[1:]:
            if len(value) > 0:
                value += ':'
            value += i
        if len(value) > 0:
            while (ord(value[0]) <= 32):
                value = value[1:]
                if len(value) <= 0:
                    break
        if len(value) > 0:
            while (ord(value[-1]) <= 32):
                value = value[:-1]
                if len(value) <= 0:
                    break

        if key in request['headers']:
            raise RuntimeError("Got 2 same headers ({key})".format(key=key))
        else:
            request['headers'][key] = value
        if len(request['headers']) >= cfg['max_header_count']:
            raise RuntimeError("Too many headers")

    for i in {'http_version', 'url', 'method'}:
        request[i] = request[i].decode('utf-8')

    if '..' in request["url"] or "//" in request["url"]:
        raise RuntimeError("Unallowed request: {url}".format(**request))

    for i in request['args']:
        request['args'][i] = request['args'][i].decode('utf-8')

    if 'Content-Length' in request['headers']:
        _len = int(request['headers']['Content-Length'])
        if _len >= cfg['max_data_length']:
            raise RuntimeError("Too much data")
        request['data'] = conn.recv(_len)
    return request


def pop_zeros(conn):
    """
        pop empty bytes from socket till get real data
    """
    while True:
        s = conn.recv(1, PEEK_FLAGS)
        if len(s) <= 0 or ord(s) > 32:
            return
        conn.recv(1)
