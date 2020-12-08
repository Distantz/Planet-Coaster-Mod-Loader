import zipfile
import requests
import shutil
import os
import sys

class Updater():
	def __init__(self):
		pass

	def check_update(self, version):
		tag = self.get_tag()
		if float(version) < float(tag):

			return True

		else:
			return False

	def get_tag(self):
		response = requests.get("https://api.github.com/repos/Distantz/Planet-Coaster-Mod-Loader/releases/latest")
		print(response)
		return response.json()["tag_name"]

	def get_desc(self):
		response = requests.get("https://api.github.com/repos/Distantz/Planet-Coaster-Mod-Loader/releases/latest")
		return response.json()["body"]
