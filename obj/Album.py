from .Track import Track

class Album:
	def __init__(self, body):
		self.id = body["ALB_ID"]
		self.title = body["ALB_TITLE"]
		self.picture = body["ALB_PICTURE"]
		self.artist = {
			'id': body["ART_ID"],
			'name': body["ART_NAME"]
		}
		self.label = body["LABEL_NAME"]
		self.discTotal = body["NUMBER_DISK"]
		if "NUMBER_TRACK" in body:
			self.trackTotal = body["NUMBER_TRACK"]
		self.explicit = body["EXPLICIT_ALBUM_CONTENT"]["EXPLICIT_LYRICS_STATUS"] > 0
		self.barcode = body["UPC"] if "UPC" in body else None
		self.date = {
			'day': body["PHYSICAL_RELEASE_DATE"][8,10],
			'month': body["PHYSICAL_RELEASE_DATE"][5,7],
			'year': body["PHYSICAL_RELEASE_DATE"][0, 4]
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
		if "SONGS" in body:
			self.trackTotal = body["SONGS"]["total"]
			self.tracks = []
			for track in body["SONGS"]["data"]:
				self.tracks.append(Track(track))
