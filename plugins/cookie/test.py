#!/usr/bin/env python3

from cookie import Cookie
from cookies import Cookies

def main():
	class Parent:
		def log(self,st,_type):
			print("%s - %s"%(_type,st))
	req = {
		"headers":{
			"Cookie":["_ym_uid=1536742764474846765; _ym_d=1536742764; _ym_isad=2; PHPSESSID=28m8ba04pc2stfmqb5t27lj652; _identity=KHH55; _csrf-frontend=ABCD"]
		}
	}
	cks = Cookies(Parent(),req)
	cks.test()
	#print(cks.export())
	for i in cks.export():
		print(i)

if __name__ == '__main__':
	main()