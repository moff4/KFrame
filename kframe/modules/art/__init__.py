#!/usr/bin/env python3

from .parser import Parser
from .coder import Coder


def marshal(data, mask=None, random=True):
    """
        convert data to bytes
        mask - some mask to be applied on marshaled data
    """
    c = Coder(data, random=random)
    c.magic()
    if mask is None:
        return c.export()
    else:
        data = c.export()
        return bytes([data[i] ^ mask[i % len(mask)] for i in range(len(data))])


def unmarshal(data=None, fd=None, mask=None):
    """
        convert data as bytes() or from fd {interface : read() }
    """
    if data is None and fd is None:
        raise ValueError('Expected param "data" of "fd"')
    if data is not None and all(map(lambda x: not isinstance(data, x), {bytes, str})):
        raise ValueError('Unexpected type of "data" ({}), expected bytes or str'.format(type(data)))
    return Parser(
        mask=mask,
        fd=fd,
        data=data
    ).magic().export()
