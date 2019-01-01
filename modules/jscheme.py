#!/usr/bin/env python3


#
# obj - some object
# scheme - json scheme full of fileds "type",value","default"
# key is name of top-level object (or None) ; for log
# scheme ::= {
#   type    : type of this object : "list/dict/str/int/float"
#   value   : scheme - need for list/dict - pointer to scheme for child
#   default : default value if this object does not exists
# }
#
def apply(obj, scheme, key=None):
    def default(value):
        return value() if '__call__' in dir(value) else value
    _key = key if key is not None else "Top-level"
    extra = "" if key is None else "".join(["for ", key])
    if type(scheme) != dict:
        raise ValueError(
            "scheme must be dict {extra}".format(
                extra=extra
            )
        )
    _t = type(obj)
    if scheme['type'] in [list, "list", "array"]:
        if _t != list:
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=_t,
                    type=scheme['type'],
                    extra=extra
                )
            )
        for i in obj:
            apply(i, scheme['value'], key=_key)
    elif scheme['type'] in [dict, 'object', 'dict']:
        if _t != dict:
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=_t,
                    type=scheme['type'],
                    extra=extra
                )
            )
        for i in scheme['value']:
            boo = True
            if i not in obj and 'default' in scheme['value'][i]:
                obj[i] = default(scheme['value'][i]['default'])
                boo = False
            if i not in obj:
                raise ValueError(
                    'expected value "{value}" {extra}'.format(
                        value=scheme['type'],
                        extra=extra + ".{key}".format(
                            key=i
                        )
                    )
                )
            if boo:
                apply(
                    obj=obj[i],
                    scheme=scheme['value'][i],
                    key=i
                )
    elif scheme['type'] in [str, "string"]:
        if _t != str:
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=_t,
                    type=scheme['type'],
                    extra=extra
                )
            )
    elif scheme['type'] in [int, "int", "integer"]:
        if _t != int:
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=_t,
                    type=scheme['type'],
                    extra=extra
                )
            )
    elif scheme['type'] in [float, "float"]:
        if _t != float:
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=_t,
                    type=scheme['type'],
                    extra=extra
                )
            )
    return obj
