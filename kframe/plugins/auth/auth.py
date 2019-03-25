#!/usr/bin/env python3

import time
import binascii

from ...base.plugin import Plugin
from ...modules import jscheme
from ...modules import crypto
from ...modules import art
from ..mchunk import Mchunk
from ..stats import Stats


class Auth(Plugin):
    """
        This module is to work with sessions, cookies and SQL-storing
    """

    name = 'auth'

    def init(self, secret, **kwargs):
        """
            sercret - secret key for crypto
        """
        mch = self.P.fast_init(
            key='mchunk',
            target=Mchunk
        ) if 'mchunk' not in self else self.P.init_plugin(
            key='mchunk'
        )
        self.secret = mch.set(secret).mask()
        if 'stats' not in self:
            self.P.fast_init(key='stats', target=Stats, export=False)

        self.mask_1 = kwargs['mask_1'] if 'mask_1' in kwargs else None
        self.mask_2 = kwargs['mask_2'] if 'mask_2' in kwargs else None

        self.P.stats.init_stat(key="cookie-created", type="inc", desc="Выдано Куки-файлов")

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
                mask=self.mask_1
            )

            self.secret.unmask()
            c = crypto.Cipher(key=self.secret.get())
            self.secret.mask()

            data = art.unmarshal(
                data=c.decrypt(
                    data=data['d'],
                    iv=data['i']
                ),
                mask=self.mask_2
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

    def generate_cookie(self, user_id, **kwargs) -> bytes:
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
        }
        kwargs = dict(kwargs)
        kwargs['user_id'] = user_id
        params = {
            'user_id': 'uid',
            'expires': 'exp',
            'ip': 'ip'
        }
        for i in filter(
            lambda x: x in kwargs,
            params.keys()
        ):
            data[params[i]] = kwargs[i]
        data = art.marshal(data, mask=self.mask_2, random=True)

        self.secret.unmask()
        c = crypto.Cipher(key=self.secret.get())
        self.secret.mask()

        iv = crypto.gen_iv()
        data = c.encrypt(data=data, iv=iv)

        res = art.marshal({
            "d": data,
            "i": iv
        }, mask=self.mask_1, random=True)
        res = binascii.hexlify(res).decode()
        self.P.stats.add('cookie-created')
        return res

    def valid_cookie(self, cookie, ip=None):
        """
            return user_id if cookie is valid
            or None if cookie is not valid
        """
        cookie = binascii.unhexlify(cookie)
        cookie = self.decode_cookie(cookie)
        if any([
            cookie is None,
            cookie['exp'] is not None and (cookie['create'] + cookie['exp']) < time.time(),
            ip is not None and cookie['ip'] != ip
        ]):
            return None
        else:
            return cookie['uid']
