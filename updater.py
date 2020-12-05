import zipfile
import requests
import shutil
import os

class Updater():
	def __init__(self):
		pass
	def update(self):
		filename = "update.zip"

		response = requests.get("https://api.github.com/repos/EvanMad/hello-world/releases/latest")
		LatestURL = response.json()["assets"][0]["browser_download_url"]
		tag = response.json()["tag_name"]
		print(LatestURL)

		r = requests.get(LatestURL, allow_redirects=True)
		open(filename,"wb").write(r.content)

		pz = open(filename, 'rb')
		pack = zipfile.ZipFile(pz)
		pack.extractall()
		pz.close()
		os.remove(filename)

		#with open("VERSION","w") as out:
			#out.write(tag)

	def check_update(self, version):
		tag = self.get_tag()
		if version < tag:
			return True
		else:
			return False

	def get_tag(self):
		response = requests.get("https://api.github.com/repos/EvanMad/hello-world/releases/latest")
		return response.json()["tag_name"]