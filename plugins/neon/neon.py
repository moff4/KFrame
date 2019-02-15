#!/usr/bin/env python3
import os
import ssl
import time
import random
import socket
import binascii
import threading as th

from ...base.plugin import Plugin
from ...modules import crypto
from ..stats import stats_scheme
from .request import Request
from .responses import Response, StaticResponse
from .utils import *
from .exceptions import ResponseError
from .parser import pop_zeros


class Neon(Plugin):
    def init(self, **kwargs):
        try:
            defaults = {
                'allowed_hosts': {'any'},
                'only_local_hosts': False,
                'http_port': 8080,
                'https_port': 8081,
                'use_ssl': False,
                'ca_cert': None,
                'ssl_cert': {},
                'site_directory': './var',
                'cgi_modules': [],
                'max_data_length': MAX_DATA_LEN,
                'max_header_count': MAX_HEADER_COUNT,
                'max_header_length': MAX_HEADER_LEN,
                'threading': False,
                'use_neon_server': False,
                'extra_response_types': {'response'},
                'response_settings': {
                    'cache_min': 120,
                },
                'single_request_per_socket': True,
            }
            self.cfg = {}
            for i in defaults:
                if isinstance(defaults[i], dict):
                    self.cfg[i] = dict(defaults[i])
                    self.cfg[i].update(kwargs.get(i, {}))
                else:
                    self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]

            self._run = True
            self._th = None
            self._rng = random.random() * 10**2

            self.Path = '/'

            if self.cfg['site_directory'].endswith('/'):
                self.cfg['site_directory'] = self.cfg['site_directory'][:-1]
            if self.cfg['use_ssl']:
                self.context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH, cafile=self.cfg['ca_cert'])
                if self.cfg['ssl_cert']:
                    self.context.load_cert_chain(
                        certfile=self.cfg['ssl_cert']['certfile'],
                        keyfile=self.cfg['ssl_cert']['keyfile'],
                        password=self.cfg['ssl_cert'].get('keypassword')
                    )
                if all(map(lambda x: x in self.cfg, {'certfile', 'keyfile'})):
                    self.context.load_cert_chain(
                        certfile=self.cfg['certfile'],
                        keyfile=self.cfg['keyfile'],
                        password=self.cfg.get('keypassword'),
                    )
            else:
                self.context = None

            self.P.add_plugin(key='request', target=Request, autostart=False, module=False)
            if 'response' in self.cfg['extra_response_types']:
                self.P.add_plugin(key='response', target=Response, autostart=False, module=False)
            if 'rest_response' in self.cfg['extra_response_types']:
                self.P.add_plugin(key='rest_response', target=RestResponse, autostart=False, module=False)
            if 'static_response' in self.cfg['extra_response_types']:
                self.P.add_plugin(key='static_response', target=StaticResponse, autostart=False, module=False)

            if 'stats' not in self:
                self.P.add_plugin(key='stats', **stats_scheme).init_plugin(key='stats', export=False)
            if 'crypto' not in self:
                self.P.add_module(key='crypto', target=crypto).init_plugin(key='crypto', export=False)

            self.P.stats.init_stat(
                key='start-time',
                type='single',
                default=time.strftime('%H:%M:%S %d %b %Y'),
                desc='Время запуска сервера'
            )
            self.P.stats.init_stat(
                key='start-timestamp',
                type='single',
                default=int(time.time()),
                desc='Время запуска сервера'
            )
            self.P.stats.init_stat(key='requests-success', type='inc', desc='Кол-во успешных запросов')
            self.P.stats.init_stat(key='requests-failed', type='inc', desc='Кол-во ошибочных запросов')
            self.P.stats.init_stat(key='connections', type='inc', desc='Кол-во соединений')
            self.P.stats.init_stat(key='aver-response-time', type='aver', desc='Среднее время ответа')

        except Exception as e:
            print(e)
            self.FATAL = True
            self.errmsg = '{}: {}'.format(self.name, str(e))

    # ========================================================================
    #                                  UTILS
    # ========================================================================

    def gen_id(self):
        self._rng += 1
        st = binascii.hexlify(self.P.crypto._hash(str(self._rng).encode('utf-8'))[:2]).decode()
        az = []
        while len(st) > 0:
            az.append(st[:4])
            az.append('-')
            st = st[4:]
        return ''.join(az[:-1])

    def open_port(self, use_ssl=False, port=80):
        j = 1
        while j <= 3:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', port))
                sock.listen(5)
                sock.settimeout(60 * 3600)
                return sock
            except Exception as e:
                time.sleep(j * 5)
                self.Debug('open-port {} : {}', port, e)
            j += 1
        raise RuntimeError('Could not open port (%s)' % (port))

    #
    # handler of original connection
    # return Response Object
    #
    def get(self, req):
        def dirs(path):
            if not req.url.endswith('/'):
                req.url += '/'
            return DIR_TEMPLATE.format(
                cells=''.join(
                    [
                        DIR_CELL_TEMPLATE.format(
                            filename=file,
                            **req.dict()
                        )
                        for file in os.listdir(path)
                    ]
                ),
                **req.dict()
            )
        path = self.cfg['site_directory'] + req.url
        code = 200
        try:
            if os.path.isdir(path):
                data = dirs(path)
                headers = [CONTENT_HTML]
            else:
                req.static_file(path)
                data = None
            code = req.resp.code
        except Exception as e:
            self.Error(e)
            data = NOT_FOUND
            headers = [CONTENT_HTML, 'Connection: close']
            code = 404
        if data is not None:
            req.resp.set_data(data)
            req.resp.add_headers(headers)
        req.resp.set_code(code)
        return req.resp

    # return True if need to keep-alive socket
    def choose_module(self, request):
        _t = time.time()
        res = None
        module = None
        if request.method not in HTTP_METHODS:
            request.Debug('{ip}: Unallowed method "{method}" ({url})', **request.dict())
            return False
        elif request.http_version not in HTTP_VERSIONS:
            request.Debug('{ip}: Unallowed version "{method}" ({url})', **request.dict())
            return False
        elif 'Host' not in request.headers:
            request.Debug('{ip}: No Host passed ({url})', **request.dict())
            return False
        elif request.headers['Host'] not in self.cfg['allowed_hosts'] and 'any' not in self.cfg['allowed_hosts']:
            request.Debug('{ip}: Invalid Header-Host "{}"', request.headers['Host'], **request.dict())
            return False
        else:
            modules = sorted(
                list(
                    filter(
                        lambda x: request.url.startswith(x.Path),
                        self.cfg['cgi_modules']
                    )
                ),
                reverse=True,
                key=lambda x: len(x.Path)
            )
            if len(modules) > 0:
                module = modules[0]
            elif self.cfg['use_neon_server']:
                module = self
            else:
                module = None
            if module is None:
                request.Debug('{ip}: Handler not found ({url})'.format(**request.dict()))
            else:
                request.Debug('Found handler: {name}'.format(name=module.name))
                self.P.stats.init_and_add('choose_module_{name}'.format(name=module.name), type='inc')
                try:
                    res = getattr(
                        module,
                        request.method.lower()
                    )(request)
                except ResponseError as e:
                    res = self.P.init_plugin(
                        key='response',
                        code=e.status,
                        headers=e.headers,
                        data=e.message,
                    )
                except Exception as e:
                    request.Error('cgi handler: {ex}'.format(ex=e))
                    request.Trace('cgi handler:')
                    res = self.P.init_plugin(
                        key='response',
                        code=500,
                        headers=[CONTENT_HTML],
                        data=SMTH_HAPPENED,
                    )
        if res is None:
            res = request.resp
        request.send(res)
        request.Notify('[{ip}] {code} : {method} {url} {args}', code=res.code, **request.dict())
        self.P.stats.init_and_add(
            'module_{name}_answer_{code}'.format(
                name='None' if module is None else module.name,
                code=res.code
            ),
            type='inc'
        )
        _t = time.time() - _t
        self.P.stats.add(key="aver-response-time", value=_t)
        if 200 <= res.code < 300:
            self.P.stats.init_and_add(
                key="{name}-aver-response-time".format(
                    name='None' if module is None else module.name
                ),
                type="aver",
                value=_t
            )
        try:
            request.after_handler()
        except Exception as e:
            request.Error('cgi after-handler: {ex}'.format(ex=e))
            request.Trace('cgi after-handler:')
        return request.headers.get('Connection') == 'keep-alive'

    # ========================================================================
    #                              DEMON TOOLS
    # ========================================================================

    def check_thread(self):
        try:
            for i in self.thread_list:
                if not i.is_alive():
                    i.join()
                    self.thread_list.pop(self.thread_list.index(i))
        except Exception as e:
            self.Error('check_thread: {}', e)

    def wrap_ssl(self, conn):
        if self.context is not None:
            self.Debug('Gonna wrap')
            conn = self.context.wrap_socket(conn, server_side=True)
            self.Debug('Done wrap')
        return conn

    def __alt_run(self, sock, port, _ssl=False):
        @recursion
        def another_deal(conn, addr):
            try:
                self.P.stats.add(key='connections')
                conn = self.wrap_ssl(conn) if _ssl else conn
                request = self.P.init_plugin(key='request', conn=conn, addr=addr, id=self.gen_id(), **self.cfg)
                if request.FATAL:
                    self.Error('request-init: {}'.format(request.errmsg))
                    conn.close()
                else:
                    request.set_ssl(_ssl)
                    request.set_secure((self.cfg['use_ssl'] and _ssl) or (not self.cfg['use_ssl']))
                    if self.choose_module(request) and not self.cfg['single_request_per_socket']:
                        try:
                            pop_zeros(conn)
                        except Exception as e:
                            self.Warring('pop-zeros: {}', e)
                        another_deal.call(conn, addr)
                    else:
                        conn.close()

            except Exception as e:
                conn.close()
                self.Warring('Another-Deal: ({}) {}', addr[0], e)
                self.Trace('Another-Deal: ({}) ', addr[0])
        self.Debug('Starting my work on port {}!', port)
        try:
            self.thread_list = []
            while self._run:
                try:
                    conn, addr = sock.accept()
                    self.Debug('New: {ip}:{port}', ip=addr[0], port=addr[1])
                except socket.timeout as e:  # time to reopen port
                    try:
                        sock.close()
                    except Exception as e:
                        self('Err while opennig port')
                        time.sleep(5)
                    finally:
                        if self.cfg['use_ssl']:
                            port = https_port
                        else:
                            port = http_port
                        sock = self.open_port(use_ssl=_ssl, port=port)

                if (
                    not self.cfg['only_local_hosts']
                ) or (
                    self.cfg['only_local_hosts'] and is_local_ip(addr)
                ):
                    if self.cfg['threading']:
                        t = th.Thread(target=another_deal, args=(conn, addr))
                        t.start()
                        self.thread_list.append(t)
                    else:
                        another_deal(conn, addr)
                else:
                    self.Debug('Not private_ip')
                    conn.close()
                time.sleep(0.1)
                self.check_thread()

        except Exception as e:
            self.Error('Listen port error: {}', e)
            time.sleep(5)
        except KeyboardInterrupt:
            self.Notify('got SIGINT: stopping')
        finally:
            sock.close()

    def _open(self):
        def open(port):
            try:
                # in Windows u cannot stop program while it's listening the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('0.0.0.0', port))
                sock.close()
            except Exception:
                pass
        if self.cfg['use_ssl']:
            open(self.cfg['https_port'])
        open(self.cfg['http_port'])

    def _loop(self):
        try:
            self._threads = []
            if self.cfg['use_ssl']:
                self._threads.append(
                    [
                        th.Thread(
                            target=self.__alt_run,
                            args=[
                                self.open_port(use_ssl=True, port=self.cfg['https_port']),
                                self.cfg['https_port'],
                                True
                            ]
                        ),
                        self.cfg['https_port']
                    ]
                )
                self._threads[-1][0].start()
                self._threads.append(
                    [
                        th.Thread(
                            target=self.__alt_run, args=[
                                self.open_port(use_ssl=False, port=self.cfg['http_port']),
                                self.cfg['http_port'],
                                False
                            ]
                        ),
                        self.cfg['http_port']
                    ]
                )
                self._threads[-1][0].start()
                while self._run:
                    time.sleep(1)
            else:
                self.__alt_run(
                    sock=self.open_port(
                        use_ssl=False,
                        port=self.cfg['http_port']
                    ),
                    _ssl=False,
                    port=self.cfg['http_port']
                )
        except Exception as e:
            self.Error('run: Exception: {}', e)
        except KeyboardInterrupt:
            self.Notify('run: KeyboardInterrupt')
        finally:
            self._run = False
            self.Notify('socket closed')
            self._open()
            for i in self._threads:
                i[0].join()
        self.Notify('Finishing my work!')

    # ========================================================================
    #                                USER API
    # ========================================================================

    #
    # add new cgi_modules
    # Module - Module/Object that has special interface:
    #   Path - str - begginig of all urls that this module handle
    #   get(request)        - handler for GET requests      ; if not presented -> send 404 by default
    #   post(requests)      - handler for POST requests     ; if not presented -> send 404 by default
    #   head(requests)      - handler for HEAD requests     ; if not presented -> send 404 by default
    #   put(requests)       - handler for PUT requests      ; if not presented -> send 404 by default
    #   delete(requests)    - handler for DELETE requests   ; if not presented -> send 404 by default
    #   options(requests)   - handler for OPTIONS requests  ; if not presented -> send 404 by default
    #
    def add_site_module(self, module, path=None):
        if path is not None and not hasattr(module, 'Path'):
            setattr(module, 'Path', path)
        self.cfg['cgi_modules'].append(module)

    #
    # start web-server
    #
    def start(self):
        self._th = th.Thread(target=self._loop)
        self._th.start()

    #
    # stop web-server
    #
    def stop(self, wait=True):
        self._run = False
        self._open()
        if wait and self._th is not None:
            self._th.join()
