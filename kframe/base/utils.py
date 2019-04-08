#!/usr/bin/env python3


def copy_n_update(d1, *args, **kwargs):
    d1 = d1.copy()
    d1.update(*args, **kwargs)
    return d1
