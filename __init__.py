from urllib.request import urlopen
from urllib.parse import quote_plus
import requests
import json
import re

from .obj.Track import Track
from .obj.Album import Album
from .utils import getBlowfishKey

class Deezer:
	def __init__(self):
		self.apiUrl = "http://www.deezer.com/ajax/gw-light.php"
		self.legacyApiUrl = "https://api.deezer.com/"
		self.httpHeaders = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
			"Content-Language": "en-US",
			"Cache-Control": "max-age=0",
			"Accept": "*/*",
			"Accept-Charset": "utf-8,ISO-8859-1;q=0.7,*;q=0.3",
			"Accept-Language": "en-US,en;q=0.9,en-US;q=0.8,en;q=0.7",
			"Connection": "keep-alive"
			}
		self.albumPicturesHost = "https://e-cdns-images.dzcdn.net/images/cover/"
		self.artistPictureHost = "https://e-cdns-images.dzcdn.net/images/artist/"
		self.user = {}
		self.session = requests.Session()

	def getToken(self):
		tokenData = self.apiCall('deezer.getUserData')
		return tokenData["results"]["checkForm"]

	def apiCall(self, method, args={}):
		result = self.session.post(
			self.apiUrl,
			params = {
				'api_version' : "1.0",
				'api_token' : 'null' if method == 'deezer.getUserData' else self.getToken(),
				'input' : '3',
				'method' : method
			},
			data = json.dumps(args),
			headers = self.httpHeaders
		)
		return json.loads(result.text)

	def legacyApiCall(self, method, args={}):
		result = self.session.get(
			self.legacyApiUrl+method,
			params = args,
			headers = self.httpHeaders
		)
		result_json = json.loads(result.text)
		if 'error' in result_json.keys():
			raise APIError()
		return result_json

	def login(self, email, password, reCaptchaToken):
		checkFormLogin = self.apiCall("deezer.getUserData")
		login = self.session.post(
			"https://www.deezer.com/ajax/action.php",
			data={
				'type':'login',
				'mail':email,
				'password':password,
				'checkFormLogin':checkFormLogin['results']['checkFormLogin'],
				'reCaptchaToken': reCaptchaToken
			},
			headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}.update(self.httpHeaders)
		)
		if not 'success' in login.text:
			return False
		userData = self.apiCall("deezer.getUserData")
		self.user = {
			'email': email,
			'id': userData["results"]["USER"]["USER_ID"],
			'name': userData["results"]["USER"]["BLOG_NAME"],
			'picture': userData["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in userData["results"]["USER"] else ""
		}
		return True

	def loginViaArl(self, token):
		userData = self.apiCall("deezer.getUserData")
		self.user = {
			'id': userData["results"]["USER"]["USER_ID"],
			'name': userData["results"]["USER"]["BLOG_NAME"],
			'picture': userData["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in userData["results"]["USER"] else ""

	def getTrack(self, id):
		if (int(id)<0):
			body = self.apiCall('song.getData', {'sng_id': id})
		else:
			body = self.apiCall('deezer.pageTrack', {'sng_id': id})
			if 'LYRICS' in body['results']:
				body['results']['DATA']['LYRICS'] = body['results']['LYRICS']
			body['results'] = body['results']['DATA']
		return Track(body['results'])

	def getTracks(self, ids):
		tracksArray = []
		body = self.apiCall('song.getListData', {'sng_ids': ids})
		for track in body['results']['data']:
			tracksArray.append(Track(track))
		return tracksArray

	def getAlbum(self, id):
		body = apiCall('album.getData', {'alb_id': id})
		return Album(body['results'])

	def getAlbumTracks(self, id):
		tracksArray = []
		body = self.apiCall('song.getListByAlbum', {'alb_id': id, 'nb': -1})
		for track in body['results']['data']:
			tracksArray.append(Track(track))
		return tracksArray

	def getArtist(self, id):
		body = apiCall('deezer.pageArtist', {'art_id': id})
		return body

	def getPlaylist(self, id):
		body = apiCall('deezer.pagePlaylist', {'playlist_id': id})
		return body

	def getPlaylistTracks(self, id):
		tracksArray = []
		body = self.apiCall('playlist.getSongs', {'playlist_id': id, 'nb': -1})
		for track in body['results']['data']:
			_track = Track(track)
			_track.position = body['results']['data'].index(track)
			tracksArray.append(_track)
		return tracksArray

	def getLyrics(self, id):
		body = self.apiCall('song.getLyrics', {'sng_id': id})
		lyr = {}
		lyr['unsyncLyrics'] = {
			'description': "",
			'lyrics': body["results"]["LYRICS_TEXT"]
		}
		lyr['syncLyrics'] = ""
		for i in range(len(body["results"]["LYRICS_SYNC_JSON"])):
			if "lrc_timestamp" in body["results"]["LYRICS_SYNC_JSON"][i]:
				lyr['syncLyrics'] += body["results"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + body["results"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
			elif i+1 < len(body["results"]["LYRICS_SYNC_JSON"]):
				lyr['syncLyrics'] += body["results"]["LYRICS_SYNC_JSON"][i+1]["lrc_timestamp"] + body["results"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
		return lyr

	def legacyGetUserPlaylist(self, id):
		body = self.legacyApiCall('user/'+id+'/playlists', {'limit': -1})
		return body

	def legacyGetTrack(self, id):
		body = self.legacyApiCall('track/'+id)
		return body

	def legacyGetTrackByISRC(self, isrc):
		body = self.legacyApiCall('track/isrc:'+isrc)
		return body

	def legacyGetChartsTopCountry(self):
		return self.legacyGetUserPlaylist('637006841')

	def legacyGetPlaylist(self, id):
		body = self.legacyApiCall('playlist/'+id)
		return body

	def legacyGetPlaylistTracks(self, id):
		body = self.legacyApiCall('playlist/'+id+'/tracks', {'limit': -1})
		return body

	def legacyGetAlbum(self, id):
		body = self.legacyApiCall('album/'+id)
		return body

	def legacyGetAlbumByUPC(self, upc):
		body = self.legacyApiCall('album/upc:'+upc)

	def legacyGetAlbumTracks(self, id):
		body = self.legacyApiCall('album/'+id+'/tracks', {'limit': -1})
		return body

	def legacyGetArtistAlbums(self, id):
		body = self.legacyApiCall('artist/'+id+'/albums', {'limit': -1})
		return body

	def legacySearch(self, term, type, limit = 30):
		body = self.legacyApiCall('search/'+type, {'q': term, 'limit': limit})
		return body

	def decryptTrack(self, trackId, input, output):
	    response = open(input, 'rb')
	    outfile = open(output, 'wb')
	    cipher = blowfish.Cipher(str.encode(getBlowfishKey(trackId)))
	    i=0
	    while True:
	        chunk = response.read(2048)
	        if not chunk:
	            break
	        if (i % 3)==0 and len(chunk)==2048:
	            chunk = b"".join(cipher.decrypt_cbc(chunk,b"\x00\x01\x02\x03\x04\x05\x06\x07"))
	        outfile.write(chunk)
	        i += 1

class APIError(Exception):
    pass
