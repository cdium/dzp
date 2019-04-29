from ..utils import md5
from ..utils import ecbCrypt

class Track:
	def __init__(self, body):
		self.id = body["SNG_ID"]
		self.title = body["SNG_TITLE"]+(" "+body["VERSION"] if body["VERSION"] else "")
		self.duration = body["DURATION"]
		self.MD5 = body["MD5_ORIGIN"]
		self.mediaVersion = body["MEDIA_VERSION"]
		if (int(self.id) < 0):
			self.filesize = int(body["FILESIZE"])
			self.album = {
				'id': 0,
				'title': body["ALB_TITLE"],
				'picture': body["ALB_PICTURE"]}
			self.artist = {
				'id': 0,
				'name': body["ART_NAME"]
				}
			self.artists = [self.artist]
			self.recordType = -1
		else:
			self.filesize = {
				'default': int(body["FILESIZE"]),
				'mp3_128': int(body["FILESIZE_MP3_128"]),
				'mp3_320': int(body["FILESIZE_MP3_320"]),
				'flac': int(body["FILESIZE_FLAC"]),
			}
			self.fallbackId = body["FALLBACK"]["SNG_ID"] if "FALLBACK" in body else 0
			self.album = {
				'id': body["ALB_ID"],
				'title': body["ALB_TITLE"],
				'picture': body["ALB_PICTURE"]
			}
			self.artist = {
				'id': body["ART_ID"],
				'name': body["ART_NAME"],
				'picture': body["ART_PICTURE"] if "ART_PICTURE" in body else None
			}
			self.date = {
				'day': body["PHYSICAL_RELEASE_DATE"][8:10],
				'month': body["PHYSICAL_RELEASE_DATE"][5:7],
				'year': body["PHYSICAL_RELEASE_DATE"][0:4]
			}
			if "ARTISTS" in body:
				self.artists = []
				for artist in body["ARTISTS"]:
					if artist["__TYPE__"] == "artist":
						self.artists.append({
							'id': artist["ART_ID"],
							'name': artist["ART_NAME"],
							'picture': artist["ART_PICTURE"]
						})
			else:
				self.artistsString = []
				if "main_artist" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["main_artist"])
				elif "mainartist" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["mainartist"])
				if "artist" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["artist"])
				if "featuredartist" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["featuredartist"])
				if "featuring" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["featuring"])
				if "associatedperformer" in body["SNG_CONTRIBUTORS"]:
					self.artistsString.append(body["SNG_CONTRIBUTORS"]["associatedperformer"])
				if not self.artistsString:
					self.artistsString.append(self.artist["name"])
			self.gain = body["GAIN"] if "GAIN" in body else None
			self.discNumber = body["DISK_NUMBER"] if "DISK_NUMBER" in body else None
			self.trackNumber = body["TRACK_NUMBER"] if "TRACK_NUMBER" in body else None
			self.explicit = body["EXPLICIT_LYRICS"] if "EXPLICIT_LYRICS" in body else None
			self.ISRC = body["ISRC"] if "ISRC" in body else None
			self.contributor = body["SNG_CONTRIBUTORS"] if "SNG_CONTRIBUTORS" in body else None
			self.lyricsId = body["LYRICS_ID"] if "LYRICS_ID" in body else None
			self.copyright = body["COPYRIGHT"] if "COPYRIGHT" in body else None
			self.recordType = body["TYPE"] if "TYPE" in body else None
			self.contributor = body["SNG_CONTRIBUTORS"] if "SNG_CONTRIBUTORS" in body else None
			self.recordType = body["TYPE"] if "TYPE" in body else None
			if "LYRICS" in body:
				self.unsyncLyrics = {
					'description': "",
					'lyrics': body["LYRICS"]["LYRICS_TEXT"]
				}
				self.syncLyrics = ""
				for i in range(len(body["LYRICS"]["LYRICS_SYNC_JSON"])):
					if "lrc_timestamp" in body["LYRICS"]["LYRICS_SYNC_JSON"][i]:
						self.syncLyrics += body["LYRICS"]["LYRICS_SYNC_JSON"][i]["lrc_timestamp"] + body["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"
					elif i+1 < len(body["LYRICS"]["LYRICS_SYNC_JSON"]):
						self.syncLyrics += body["LYRICS"]["LYRICS_SYNC_JSON"][i+1]["lrc_timestamp"] + body["LYRICS"]["LYRICS_SYNC_JSON"][i]["line"]+"\r\n"

	def getDownloadUrl(self, format):
		if not self.MD5:
			return False
		urlPart = self.MD5+"¤"+str(format)+"¤"+self.id+"¤"+self.mediaVersion
		md5val = md5(urlPart)
		step2 = b'\xa4'.join([str.encode(md5val), str.encode(urlPart)])
		while len(step2)%16 > 0:
			step2 += b'.'
		urlPart = ecbCrypt(b'jo6aey6haid2Teih', step2)
		return "https://e-cdns-proxy-" + self.MD5[0] + ".dzcdn.net/mobile/1/" + urlPart.decode("utf-8")
