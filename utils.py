import hashlib
import pyaes
import binascii
import blowfish

def md5(data):
	h=hashlib.new("md5")
	h.update(str.encode(data) if isinstance(data, str) else data)
	return h.hexdigest()

def ecbCrypt(key, data):
	res = b''
	for x in range(int(len(data)/16)):
		res += binascii.hexlify(pyaes.AESModeOfOperationECB(key).encrypt(data[:16]))
		data = data[16:]
	return res

def getBlowfishKey(trackId):
	SECRET = 'g4el58wc'+'0zvf9na1'
	idMd5 = md5(trackId)
	bfKey = ""
	for i in range(16):
		bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i+16]) ^ ord(SECRET[i]))
	return bfKey
