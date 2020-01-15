#!/usr/bin/env python3
from urllib.request import urlopen
from urllib.parse import quote_plus
import requests
import json
import re
import blowfish

from .utils import getBlowfishKey
from .utils import md5
from .utils import ecbCrypt

class Deezer:
	def __init__(self):
		self.apiUrl = "http://www.deezer.com/ajax/gw-light.php"
		self.legacyApiUrl = "https://api.deezer.com/"
		self.mobileApiUrl = "https://api.deezer.com/1.0/gateway.php"
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
		self.sid = None

	def getToken(self):
		tokenData = self.apiCall('deezer.getUserData')
		return tokenData["results"]["checkForm"]

	def getSID(self):
		result = self.session.get(
			"https://www.deezer.com",
			headers = self.httpHeaders
		)
		self.sid = self.session.cookies.get_dict()['sid']
		return self.sid

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


	def mobileApiCall(self, method, args):
		result = self.session.post(
			self.mobileApiUrl,
			params = {
				'api_key': "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE",
				'sid': self.sid if self.sid else self.getSID(),
				'method': method,
				'output': "3",
				'input': "3"
			},
			data = json.dumps(args),
			headers = self.httpHeaders
		)
		return json.loads(result.text)

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

	def loginViaArl(self, arl):
		cookie_obj = requests.cookies.create_cookie(
			domain='deezer.com',
			name='arl',
			value=arl,
			path="/",
			rest={'HttpOnly': True}
		)
		self.session.cookies.set_cookie(cookie_obj)
		userData = self.apiCall("deezer.getUserData")
		if (userData["results"]["USER"]["USER_ID"] == 0):
			return False
		self.user = {
			'id': userData["results"]["USER"]["USER_ID"],
			'name': userData["results"]["USER"]["BLOG_NAME"],
			'picture': userData["results"]["USER"]["USER_PICTURE"] if "USER_PICTURE" in userData["results"]["USER"] else ""
		}
		return True

	def getTrack(self, id):
		if (int(id)<0):
			body = self.apiCall('song.getData', {'sng_id': id})
		else:
			body = self.apiCall('deezer.pageTrack', {'sng_id': id})
			if 'LYRICS' in body['results']:
				body['results']['DATA']['LYRICS'] = body['results']['LYRICS']
			body['results'] = body['results']['DATA']
		return self.parseTrack(body['results'])

	def getTracks(self, ids):
		tracksArray = []
		body = self.apiCall('song.getListData', {'sng_ids': ids})
		errors = 0
		for i in range(len(ids)):
			if ids[i] != 0:
				tracksArray.append(self.parseTrack(body['results']['data'][i-errors]))
			else:
				errors += 1
				tracksArray.append({
					'id': 0,
				    'title': '',
				    'duration': 0,
				    'MD5': 0,
				    'mediaVersion': 0,
				    'filesize': 0,
				    'album': {'id': 0, 'title': "", 'picture': ""},
				    'artist': {'id': 0, 'name': ""},
				    'artists': [{'id': 0, 'name': ""}],
				    'recordType': -1,
				})
		return tracksArray

	def getTrackMD5(self, id):
		body = self.mobileApiCall('song_getData', {'sng_id': id})
		return body['results']['PUID']

	def getDownloadUrl(self, track, format):
		if not track["MD5"]:
			return False
		urlPart = b'\xa4'.join([str.encode(track["MD5"]), str.encode(str(format)), str.encode(str(track["id"])), str.encode(str(track["mediaVersion"]))])
		md5val = md5(urlPart)
		step2 = str.encode(md5val)+b'\xa4'+urlPart+b'\xa4'
		while len(step2)%16 > 0:
			step2 += b'.'
		urlPart = ecbCrypt(b'jo6aey6haid2Teih', step2)
		return "https://e-cdns-proxy-" + track["MD5"][0] + ".dzcdn.net/mobile/1/" + urlPart.decode("utf-8")

	def getAlbum(self, id):
		body = apiCall('album.getData', {'alb_id': id})
		return self.parseAlbum(body['results'])

	def getAlbumTracks(self, id):
		tracksArray = []
		body = self.apiCall('song.getListByAlbum', {'alb_id': id, 'nb': -1})
		for track in body['results']['data']:
			_track = self.parseTrack(track)
			_track["position"] = body['results']['data'].index(track)
			tracksArray.append(_track)
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
			_track = self.parseTrack(track)
			_track["position"] = body['results']['data'].index(track)
			tracksArray.append(_track)
		return tracksArray

	def getArtistTopTracks(self, id):
		tracksArray = []
		body = self.apiCall('artist.getTopTrack', {art_id: id, nb: 100})
		for track in body['results']['data']:
			_track = self.parseTrack(track)
			_track["position"] = body['results']['data'].index(track)
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
	    cipher = blowfish.Cipher(str.encode(getBlowfishKey(str(trackId))))
	    i=0
	    while True:
	        chunk = response.read(2048)
	        if not chunk:
	            break
	        if (i % 3)==0 and len(chunk)==2048:
	            chunk = b"".join(cipher.decrypt_cbc(chunk,b"\x00\x01\x02\x03\x04\x05\x06\x07"))
	        outfile.write(chunk)
	        i += 1

	def parseTrack(self, body):
		result = {}
		result["id"] = body["SNG_ID"]
		result["title"] = body["SNG_TITLE"]+(" "+body["VERSION"] if body["VERSION"] else "")
		result["duration"] = body["DURATION"]
		result["MD5"] = body["MD5_ORIGIN"] if "MD5_ORIGIN" in body else None
		result["mediaVersion"] = body["MEDIA_VERSION"]
		if (int(result["id"]) < 0):
			result["filesize"] = int(body["FILESIZE"])
			result["album"] = {
				'id': 0,
				'title': body["ALB_TITLE"],
				'picture': body["ALB_PICTURE"]}
			result["artist"] = {
				'id': 0,
				'name': body["ART_NAME"]
				}
			result["artists"] = [result["artist"]]
			result["recordType"] = -1
		else:
			result["filesize"] = {
				'default': int(body["FILESIZE"]),
				'mp3_128': int(body["FILESIZE_MP3_128"]),
				'mp3_320': int(body["FILESIZE_MP3_320"]),
				'flac': int(body["FILESIZE_FLAC"]),
				'mp4_ra1': int(body["FILESIZE_MP4_RA1"]) if "FILESIZE_MP4_RA1" in body else None,
				'mp4_ra2': int(body["FILESIZE_MP4_RA2"]) if "FILESIZE_MP4_RA2" in body else None,
				'mp4_ra3': int(body["FILESIZE_MP4_RA3"]) if "FILESIZE_MP4_RA3" in body else None
			}
			result["fallbackId"] = body["FALLBACK"]["SNG_ID"] if "FALLBACK" in body else 0
			result["album"] = {
				'id': body["ALB_ID"],
				'title': body["ALB_TITLE"],
				'picture': body["ALB_PICTURE"]
			}
			result["artist"] = {
				'id': body["ART_ID"],
				'name': body["ART_NAME"],
				'picture': body["ART_PICTURE"] if "ART_PICTURE" in body else None
			}
			result["date"] = {
				'day': body["PHYSICAL_RELEASE_DATE"][8:10],
				'month': body["PHYSICAL_RELEASE_DATE"][5:7],
				'year': body["PHYSICAL_RELEASE_DATE"][0:4]
			}
			if "ARTISTS" in body:
				result["artists"] = []
				for artist in body["ARTISTS"]:
					if artist["__TYPE__"] == "artist":
						result["artists"].append({
							'id': artist["ART_ID"],
							'name': artist["ART_NAME"],
							'picture': artist["ART_PICTURE"]
						})
			else:
				result["artistsArray"] = []
				if "main_artist" in body["SNG_CONTRIBUTORS"]:
					result["artistsArray"].append(body["SNG_CONTRIBUTORS"]["main_artist"])
				elif "mainartist" in body["SNG_CONTRIBUTORS"]:
					result["artistsArray"].append(body["SNG_CONTRIBUTORS"]["mainartist"])
				if "featuredartist" in body["SNG_CONTRIBUTORS"]:
					result["artistsArray"].append(body["SNG_CONTRIBUTORS"]["featuredartist"])
				if "featuring" in body["SNG_CONTRIBUTORS"]:
					result["artistsArray"].append(body["SNG_CONTRIBUTORS"]["featuring"])
				if "associatedperformer" in body["SNG_CONTRIBUTORS"]:
					result["artistsArray"].append(body["SNG_CONTRIBUTORS"]["associatedperformer"])
				if not result["artistsArray"]:
					result["artistsArray"].append(result["artist"]["name"])
			result["gain"] = body["GAIN"] if "GAIN" in body else None
			result["discNumber"] = body["DISK_NUMBER"] if "DISK_NUMBER" in body else None
			result["trackNumber"] = body["TRACK_NUMBER"] if "TRACK_NUMBER" in body else None
			result["explicit"] = body["EXPLICIT_LYRICS"] if "EXPLICIT_LYRICS" in body else None
			result["ISRC"] = body["ISRC"] if "ISRC" in body else None
			result["contributor"] = body["SNG_CONTRIBUTORS"] if "SNG_CONTRIBUTORS" in body else None
			result["lyricsId"] = body["LYRICS_ID"] if "LYRICS_ID" in body else None
			result["copyright"] = body["COPYRIGHT"] if "COPYRIGHT" in body else None
			result["recordType"] = body["TYPE"] if "TYPE" in body else None
			result["contributor"] = body["SNG_CONTRIBUTORS"] if "SNG_CONTRIBUTORS" in body else None
			result["recordType"] = body["TYPE"] if "TYPE" in body else None
			if "LYRICS" in body:
				result["unsyncLyrics"] = {
					'description': "",
					'lyrics': body["LYRICS"]["LYRICS_TEXT"]
				}
				result["syncLyrics"] = ""
				for i in range(len(body["LYRICS"]["LYRICS_SYNC_JSON"])):
					if "lrc_timestamp" in body["LYRICS"]["LYRICS_SYNC_JSON"][i]:
						result["syncLyrics"] += body["LYRICS"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + body["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
					elif i+1 < len(body["LYRICS"]["LYRICS_SYNC_JSON"]):
						result["syncLyrics"] += body["LYRICS"]["LYRICS_SYNC_JSON"][i+1]["lrc_timestamp"] + body["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
		return result

	def parseAlbum(self, body):
		result = {}
		result["id"] = body["ALB_ID"]
		result["title"] = body["ALB_TITLE"]
		result["picture"] = body["ALB_PICTURE"]
		result["artist"] = {
			'id': body["ART_ID"],
			'name': body["ART_NAME"]
		}
		result["label"] = body["LABEL_NAME"]
		result["discTotal"] = body["NUMBER_DISK"]
		if "NUMBER_TRACK" in body:
			result["trackTotal"] = body["NUMBER_TRACK"]
		result["explicit"] = body["EXPLICIT_ALBUM_CONTENT"]["EXPLICIT_LYRICS_STATUS"] > 0
		result["barcode"] = body["UPC"] if "UPC" in body else None
		result["date"] = {
			'day': body["PHYSICAL_RELEASE_DATE"][8,10],
			'month': body["PHYSICAL_RELEASE_DATE"][5,7],
			'year': body["PHYSICAL_RELEASE_DATE"][0, 4]
		}
		if "ARTISTS" in body:
			result["artists"] = []
			for artist in body["ARTISTS"]:
				if artist["__TYPE__"] == "artist":
					result["artists"].append({
						'id': artist["ART_ID"],
						'name': artist["ART_NAME"],
						'picture': artist["ART_PICTURE"]
					})
		if "SONGS" in body:
			result["trackTotal"] = body["SONGS"]["total"]
			result["tracks"] = []
			for track in body["SONGS"]["data"]:
				result["tracks"].append(self.parseTrack(track))
		return result

class APIError(Exception):
    pass
