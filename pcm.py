import json

class meta:
	def __init__(self, metaName, metaAuthor, metaDesc):
		self.metaName = metaName
		self.metaAuthor = metaAuthor
		self.metaDesc = metaDesc

class pcm:
	def __init__(self, input_files, meta):
		self.input_files = input_files
		self.meta = meta
		self.data = {}

	def write_meta(self):
		self.data["meta"] = {}
		self.data["meta"] = ({
			"Name" : self.meta.metaName,
			"Author(s)" : self.meta.metaAuthor,
			"Desc" : self.meta.metaDesc
		})
		return self.data

	def write_pcm(self):
		self.data["Files"] = {}

		self.data = {**self.write_meta(), **self.input_files}

	def pcm_write_to_file(self, path):
		with open(path + "/mod.json", "w") as self.out:
			json.dump(self.data, self.out)
