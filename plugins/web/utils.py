#!/usr/bin/etc python3

STANDART_HEADERS = [
	"Server: kek-server",
	'Content-type: text/html; charset=utf-8',
	"Connection: close"
]

def readln(conn,max_len=2048):
	q = b' '
	st = b''
	while ord(q) != 10:
		q = conn.recv(1)
		if len(q)<=0:
			break
		if q not in [b'\n',b'\r']:
			st += q
		if len(q) >= max_len:
			raise RuntimeError("Max-len reached")
	return st

#
# takes list of headers-lines and return extended string
#
def apply_standart_headers(headers):
	for i in STANDART_HEADERS:
		# if True not in list(map(lambda x:x.startswith(i.split(':')[0]),headers)):
		# 	headers.append(i)
		key = i.split(':')[0]
		boo = False
		for j in headers:
			boo = boo or j.startswith(key)
		if not boo:
			headers.append(i)
	st = ''
	for i in headers:
		st += "%s\r\n"%(i)
	return st

#
# get smth like b'A%66C'
# return smth like b'ABC'
#
def urldecode(az):
	def pp(z):
		if z in b'ABCDEF':
			return ord(z) - ord(b'A') + 10
		elif z in b'abcdef':
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
			bz += bytes([x*16+y])
	return bz

#
# get filename and decide content-type header
# st == req['url']
#
def Content_type(st):
	extra  = ''
	st = st.split('.')[-1]
	if st in ['html','css','txt','csv','xml','js','json','php','md']:
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

	elif st in ['jpg','jpeg','png','gif','tiff']:
		type_1 = 'image'
		type_2 = st

	elif st in ['mkv','avi','mp4']:
		type_1 = 'video'
		if st in ['mp4','avi']:
			type_2 = st
		else:
			type_2 = 'webm'
	else:
		return "Content-type: text/plain"
	return "Content-type: %s/%s%s"%(type_1,type_2,extra)