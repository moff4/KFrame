#!/usr/bin/env python3

###############################################################################
#
#  This module is wrapper over cryptography library
#     If u wish, u can rewrite it saving the interface
#
#  Now here are using algorithms:
#     hash : GOST 34.11-2012 (512) Streebog
#     sign and verify: GOST R 34.10-2012
#     encrypt and decrypt: GOST R 28147 64-bit block cipher
#
###############################################################################

from os import urandom

from pygost.gost34112012512 import GOST34112012512      # hash 512bit
from pygost.gost28147 import cfb_decrypt, cfb_encrypt   # simentric
from pygost.gost3410 import CURVE_PARAMS                # crypto-param
from pygost.gost3410 import GOST3410Curve               # crypto-param
from pygost.gost3410 import prv_unmarshal               # private key unmarshal (There are no marsha)
from pygost.gost3410 import public_key                  # public key
from pygost.gost3410 import pub_marshal                 # public key marshal
from pygost.gost3410 import pub_unmarshal               # public key unmarshal
from pygost.gost3410 import sign as _sign               # signing algorithm
from pygost.gost3410 import verify as _verify           # verify signature
from pygost.gost3410_vko import kek_34102012256         # key agreement (like Diffi-Hellman)

"""
    here should be interface for
      - import and export keys ,
      - sign and verify ,
      - hashers ,
      - encrypting and decrypting algorithms
      - key agreement algorithm (like Diffi-Hellman)
"""

CURVA = GOST3410Curve(*CURVE_PARAMS["GostR3410_2012_TC26_ParamSetA"])

# =============================================================
#            import and export keys
# =============================================================


def generate_key_pair():
    """
        generates pair of keys
        return tuple ( private_key , public_key )
    """
    private = prv_unmarshal(urandom(64))
    public = public_key(CURVA, private)
    return (private, public)


def import_private_key(filename):
    """
        return key-object
    """
    with open(filename, 'r') as f:
        return eval(f.read())


def import_public_key(data=None, filename=None):
    """
        return key-object
        data - some data containing smb's public key
        filename - fileme containing smb's public key
        must be passed at least one of params
           or will be raise ValueError
    """
    if data is None and filename is None:
        raise ValueError("Expected data or filename")
    if data is None:
        with open(filename, 'rb') as f:
            data = f.read()
    return pub_unmarshal(data, mode=2012)


def export_private_key(key, filename):
    """
        export private key using filename
    """
    with open(filename, 'w') as f:
        f.write("%d" % key)


def export_public_key(key, filename=None):
    """
        export public key to file if filename was passed
        otherwise return exported data as bytes
    """
    data = pub_marshal(key, mode=2012)
    if filename is None:
        return data
    with open(filename, 'wb') as f:
        f.write(data)


# =============================================================
#             signing and verification
# =============================================================

def sign(private_key, data):
    """
        takes private key and some raw data (bytes)
        return signiture from _hash of this data
    """
    return _sign(CURVA, private_key, _hash(data), mode=2012)


def verify(public_key, sig, dgst):
    """
        takes public key , signature(bytes) and digest(bytes)
        return True if signature is for this digest(hash)
    """
    return _verify(CURVA, public_key, dgst, sig, mode=2012)


# =============================================================
#              hash and simetric cipher
# =============================================================

def _hash(data):
    """
        hash function
        takes data
        return hash
    """
    hs = GOST34112012512()
    hs.update(data)
    return hs.digest()


class _Hash(GOST34112012512):
    """
        export basic class for ability to count hash for big data
    """
    pass


def gen_iv():
    """
        generates initialization vector
    """
    return urandom(8)


def gen_ukm():
    """
        genereate User-key-material
    """
    x = 0
    for i in urandom(8):
        x = x * 256 + i
    return x


class Cipher:
    """
        class for encryting and decrypting
        can encrypt / decrypt msg of any length
    """

    def __init__(self, key):
        """
            takes key 256bytes
        """
        self._key = key

    def encrypt(self, data, iv):
        """
            encrypt data
            takes data(plaintext(bytes)) and inbitialization vector
            return bytes
        """
        return cfb_encrypt(self._key, data=data, iv=iv)

    def decrypt(self, data, iv):
        """
            decrypt data(cipher(bytes)) and initialization vector
            return bytes
        """
        return cfb_decrypt(self._key, data=data, iv=iv)

# =============================================================
#                Key agreement algorithm
# =============================================================


def diffie_hellman(private_key, public_key, user_key_material):
    """
        key-agreement algorithm (256 bit)
        takes your private_key , peers public_key and user_key_material
        return shared secret (bytes)
    """
    return kek_34102012256(CURVA, private_key, public_key, user_key_material)
