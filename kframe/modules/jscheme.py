#!/usr/bin/env python3

MAP = {
    list: list,
    'list': list,
    'array': list,
    dict: dict,
    'dict': dict,
    'object': dict,
    int: int,
    'int': int,
    'integer': int,
    'float': float,
    float: float,
    str: str,
    'str': str,
    'string': str,
    bool: bool,
    'bool': bool,
    'boolean': bool,
}


def apply(obj, scheme, key=None):
    """
        obj - some object
        scheme - json scheme full of fileds "type",value","default"
        key is name of top-level object (or None) ; for log
        scheme ::= {
          type     : type of this object : "list/dict/str/int/float"
          value    : scheme - need for list/dict - pointer to scheme for child
          default  : default value if this object does not exists
          filter   : function value -> bool - if false then raise error
          pre_call : function value -> value - will be called before cheking filter and value (for dict and list)
          post_call: function value -> value - will be called after cheking filter and value (for dict and list)
        }
    """
    def default(value):
        return value() if callable(value) else value

    _key = key if key is not None else 'Top-level'
    extra = '' if key is None else ''.join(['for ', key])
    if not isinstance(scheme, dict):
        raise ValueError(
            'scheme must be dict {extra}'.format(
                extra=extra
            )
        )
    if 'pre_call' in scheme:
        obj = scheme['pre_call'](obj)

    if scheme['type'] in MAP:
        if not isinstance(obj, MAP[scheme['type']]):
            raise ValueError(
                'expected type "{type}" {extra} ; got {src_type}'.format(
                    src_type=type(obj),
                    type=scheme['type'],
                    extra=extra
                )
            )
        elif 'filter' in scheme and not scheme['filter'](obj):
            raise ValueError(
                '"{key}" not passed filter'.format(
                    key=key,
                )
            )

        if MAP[scheme['type']] == MAP[list]:
            obj = [apply(i, scheme['value'], key=_key) for i in obj]
        elif MAP[scheme['type']] == MAP[dict]:
            unex = {i for i in obj if i not in scheme['value']}
            if unex:
                raise ValueError(
                    'Got unexpected keys: "{keys}" {extra};'.format(
                        keys='", "'.join([str(i) for i in unex]),
                        extra=extra,
                    )
                )
            if any(
                map(
                    lambda x: x not in obj and 'default' not in scheme['value'][x],
                    obj,
                )
            ):
                raise ValueError(
                    'expected value "{value}" {extra}'.format(
                        value=scheme['type'],
                        extra=extra
                    )
                )
            obj = {
                i:
                default(scheme['value'][i]['default'])
                if i not in obj else
                apply(
                    obj=obj[i],
                    scheme=scheme['value'][i],
                    key=i,
                )
                for i in scheme['value']
            }
    else:
        raise ValueError(
            'Scheme has unknown type "{}"'.format(scheme['type'])
        )

    if 'post_call' in scheme:
        obj = scheme['post_call'](obj)
    return obj
