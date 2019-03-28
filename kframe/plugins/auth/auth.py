#!/usr/bin/env python3

import time
import binascii

from kframe.base.plugin import Plugin
from kframe.modules import jscheme
from kframe.modules import crypto
from kframe.modules import art
from kframe.plugins.mchunk import Mchunk
from kframe.plugins.stats import Stats


class Auth(Plugin):
    """
        This module is to work with sessions, cookies and SQL-storing
    """

    name = 'auth'

    def init(self, secret, **kwargs):
        """
            sercret - secret key for crypto
            kwargs:
                masks - tuple(bytes, bytes) - extra sercrets (default: (None, None))
                enable_stats - bool - enable stat agregation (default: False)
        """
        defaults = {
            'masks': (None, None),
            'enable_stats': False,
        }
        self.cfg = {k: kwargs.get(k, defaults[k]) for k in defaults}

        self.secret = self.P.fast_init(target=Mchunk).set(secret).mask()
        if self.cfg['enable_stats']:
            if 'stats' not in self:
                self.P.fast_init(target=Stats, export=False)

            self.P.stats.init_stat(key='auth-created', type='event', desc='Выданные куки')
            self.P.stats.init_stat(key='auth-verify', type='event', desc='Успешно проверенные куки')
            self.P.stats.init_stat(key='auth-unverify', type='event', desc='Неуспешно проверенные куки')

        self.cookie_scheme = {
            'type': dict,
            'value': {
                'create': {
                    'type': int
                },
                'uid': {
                    'type': int,
                    'default': None
                },
                'exp': {
                    'type': int,
                    'default': None
                },
                'ip': {
                    'type': str,
                    'default': None
                },
            }
        }

    def decode_cookie(self, cookie):
        """
            return decoded cookie as dict
            or None in case of error
        """
        try:
            data = art.unmarshal(
                data=cookie,
                mask=self.cfg['masks'][0]
            )

            with self.secret:
                c = crypto.Cipher(key=self.secret.data)

            data = art.unmarshal(
                data=c.decrypt(
                    data=data['d'],
                    iv=data['i']
                ),
                mask=self.cfg['masks'][1]
            )

            return jscheme.apply(
                obj=data,
                scheme=self.cookie_scheme,
                key='cookie'
            )
        except Exception as e:
            self.Warning('decode cookie: {}', e)
            self.Trace('decode cookie: ')
            return None

# ==========================================================================
#                               USER API
# ==========================================================================

    def generate_cookie(self, user_id, **kwargs):
        """
            generate cookie
            must:
              user_id     - int - user identificator
            optional:
              expires     - int - num of seconds this cookie is valid
              ip          - str - ip addr of client
            return bytes() as value of cookie
        """
        data = {
            'create': int(time.time()),
            'uid': user_id,
        }
        kwargs['user_id'] = user_id
        params = {
            'expires': 'exp',
            'ip': 'ip'
        }
        data.update({params[i]: kwargs[i] for i in params if i in kwargs})
        data = art.marshal(data, mask=self.cfg['masks'][1], random=True)

        with self.secret:
            c = crypto.Cipher(key=self.secret.data)

        iv = crypto.gen_iv()
        data = c.encrypt(data=data, iv=iv)

        res = art.marshal(
            {
                'd': data,
                'i': iv
            },
            mask=self.cfg['masks'][0],
            random=True
        )
        res = binascii.hexlify(res).decode()
        if self.cfg['enable_stats']:
            self.P.stats.add(
                key='auth-created',
                value=user_id,
            )
        return res

    def valid_cookie(self, cookie, ip=None):
        """
            return user_id if cookie is valid
            or None if cookie is not valid
        """
        cookie = binascii.unhexlify(cookie)
        cookie = self.decode_cookie(cookie)
        if (
            cookie is None
        ) or (
            cookie['exp'] is not None and (cookie['create'] + cookie['exp']) < time.time()
        ) or (
            ip is not None and cookie['ip'] != ip
        ):
            self.P.stats.add(
                key='auth-unverify',
                value='unknown' if cookie is None else cookie['uid'],
            )
            return None
        else:
            self.P.stats.add(
                key='auth-verify',
                value=cookie['uid'],
            )
            return cookie['uid']
