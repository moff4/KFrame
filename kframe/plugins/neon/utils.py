#!/usr/bin/etc python3

private_ip = set(
    {'10.', '192.168.', '0.0.0.0', '127.0.0.'}.union(
        {('100.%s.' % i) for i in range(64, 128)}
    ).union(
        {('172.%s.' % i) for i in range(16, 32)}
    )
)

http_code_msg = {
    100: 'Continue',
    101: 'Switching Protocols',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    206: 'Partial Content',
    301: 'Moved Permanently',
    304: 'Not Modified',
    307: 'Temporary Redirect',
    308: 'Permanent Rederict',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not found',
    405: 'Method Not Allowed',
    409: 'Conflict',
    411: 'Length Required',
    418: 'I’m a teapot',
    424: 'Failed Dependency',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    504: 'Gateway Timeout',
}

HTTP_METHODS = [
    'GET',
    'POST',
    'HEAD',
    'PUT',
    'DELETE',
    'OPTIONS',
]
HTTP_VERSIONS = [
    'HTTP/1.1',
]

NOT_FOUND = '''
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL was not found on this kek-server.</p>
</body></html>
'''
SMTH_HAPPENED = '''
<html><head>
<title>500 Smth happened</title>
</head><body>
<h1>Smth happened</h1>
<p>The requested URL found error this kek-server.</p>
</body></html>
'''

DIR_TEMPLATE = '''
<html><head>
<title>kek-server</title>
</head><body>
<h1>{url}</h1>
<ul>
{cells}
</ul>
</body></html>
'''
DIR_CELL_TEMPLATE = '''
<li><a href="{url}{filename}">{filename}</a></li>
'''

CONTENT_HTML = {'Content-type': 'text/html; charset=utf-8'}
CONTENT_JS = {'Content-type': 'application/javascript; charset=utf-8'}
CONTENT_JSON = {'Content-type': 'text/json'}

STANDART_HEADERS = {
    'Server': 'kek-server',
    'Content-type': 'text/html; charset=utf-8',
    'Accept-Ranges': 'bytes',
}


MAX_DATA_LEN = 4 * 2**10
MAX_HEADER_COUNT = 32
MAX_HEADER_LEN = 2 * 2**10


def readln(conn, max_len=2048) -> bytes:
    q = b' '
    st = b''
    while ord(q) != 10:
        q = conn.recv(1)
        if len(q) <= 0:
            break
        if q not in {b'\n', b'\r'}:
            st += q
        if len(q) >= max_len:
            raise RuntimeError('Max-len reached')
    return st


#
# takes dict of headers-lines and return extended dict of str
#
def apply_standart_headers(headers: dict) -> dict:
    headers.update(
        {
            k: STANDART_HEADERS[k]
            for k in filter(
                lambda x: x not in headers,
                STANDART_HEADERS.keys(),
            )
        }
    )
    return headers


def urldecode(az) -> bytes:
    """
        get smth like b'A%66C'
        return smth like b'ABC'
    """
    def pp(z):
        if z in {b'A', b'B', b'C', b'D', b'E', b'F'}:
            return ord(z) - ord(b'A') + 10
        elif z in {b'a', b'b', b'c', b'd', b'e', b'f'}:
            return ord(z) - ord(b'a') + 10
        else:
            return ord(z) - ord(b'0')
    bz = b''
    while len(az) > 0:
        if az[:1] != b'%':
            bz += az[:1]
            az = az[1:]
        else:
            az = az[1:]
            x = az[:1]
            az = az[1:]
            y = az[:1]
            az = az[1:]
            x = pp(x)
            y = pp(y)
            bz += bytes([x * 16 + y])
    return bz


def Content_type(st) -> str:
    """
        get filename and decide content-type header
        st == req.url
    """
    extra = ''
    st = st.split('.')[-1]
    if st in {'html', 'css', 'txt', 'csv', 'xml', 'js', 'json', 'php', 'md'}:
        type_1 = 'text'
        if st == 'js':
            type_2 = 'javascript'
        elif st == 'md':
            type_2 = 'markdown'
        elif st == 'html':
            type_2 = st
            extra = '; charset=utf-8'
        else:
            type_2 = st

    elif st in {'jpg', 'jpeg', 'png', 'gif', 'tiff'}:
        type_1 = 'image'
        type_2 = st

    elif st in {'mkv', 'avi', 'mp4'}:
        type_1 = 'video'
        if st in {'mp4', 'avi'}:
            type_2 = st
        else:
            type_2 = 'webm'
    else:
        return {'Content-type': 'text/plain'}
    return {'Content-type': '{}/{}{}'.format(type_1, type_2, extra)}


def is_local_ip(addr) -> bool:
    return any(
        map(
            lambda x: addr.startswith(x),
            private_ip
        )
    )
