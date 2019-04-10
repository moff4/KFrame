#!/usr/bin/env python3


def encode_to_UTF8(data):
    try:
        return data.encode('UTF-8')
    except UnicodeEncodeError as e:
        return False
    except Exception as e:
        raise e


def try_decode_UTF8(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    except Exception as e:
        raise e
