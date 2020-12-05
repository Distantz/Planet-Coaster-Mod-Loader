# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2012, Python File Format Interface
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#	 * Redistributions of source code must retain the above copyright
#	   notice, this list of conditions and the following disclaimer.
#
#	 * Redistributions in binary form must reproduce the above
#	   copyright notice, this list of conditions and the following
#	   disclaimer in the documentation and/or other materials provided
#	   with the distribution.
#
#	 * Neither the name of the Python File Format Interface
#	   project nor the names of its contributors may be used to endorse
#	   or promote products derived from this software without specific
#	   prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENSE BLOCK *****
import itertools
import struct
import os
import re
import io
import zlib
import pyffi.object_models.xml
import pyffi.object_models.common
import pyffi.object_models

from pyffi_ext.formats.ms2 import Ms2Format

MAX_UINT32 = 4294967295


def djb(s):
	# calculates DJB hash for string s
	# from https://gist.github.com/mengzhuo/180cd6be8ba9e2743753#file-hash_djb2-py
	hash = 5381
	for x in s:
		hash = (( hash << 5) + hash) + ord(x)
	return hash & 0xFFFFFFFF

	
def get_sized_bytes(data, pos):
	"""Returns content of sized string from bytes. Pos is the position of uint size tag in data str"""
	size = struct.unpack("<I", data[pos:pos+4])[0]
	# print("size",size, data[pos+4 : pos+size+4])
	# todo: this acutally has to reaad size bytes from its proper buffer
	# it only works here because there is no buffer
	# print("size",size, data[pos+4 : pos+30])
	return data[pos+4 : pos+4+size]


class OvlFormat(pyffi.object_models.xml.FileFormat):
	"""This class implements the Ovl format."""
	xml_file_name = 'ovl.xml'
	# where to look for ovl.xml and in what order:
	# OVLXMLPATH env var, or OvlFormat module directory
	xml_file_path = [os.getenv('OVLXMLPATH'), os.path.dirname(__file__)]
	# file name regular expression match
	RE_FILENAME = re.compile(r'^.*\.ovl$', re.IGNORECASE)
	# used for comparing floats
	_EPSILON = 0.0001

	# basic types
	int = pyffi.object_models.common.Int
	uint64 = pyffi.object_models.common.UInt64
	uint = pyffi.object_models.common.UInt
	byte = pyffi.object_models.common.Byte
	ubyte = pyffi.object_models.common.UByte
	char = pyffi.object_models.common.Char
	short = pyffi.object_models.common.Short
	ushort = pyffi.object_models.common.UShort
	float = pyffi.object_models.common.Float
	# SizedString = pyffi.object_models.common.SizedString
	ZString = pyffi.object_models.common.ZString
	
	class Data(pyffi.object_models.FileFormat.Data):
		"""A class to contain the actual Ovl data."""
		def __init__(self, progress_callback = None):
			"""Class initialisation
			
			:param progresss_callback: A function to call whenever we want to 
				report updated progress. It can be called with 3 arguments, the
				last two of which are optional. There is the message to display,
				the progress bar value, and progress bar maximum.
			:type progress_callback: function
			"""
			self.version = 0
			self.flag_2 = 0
			self.last_print = None
			self.header = OvlFormat.Header()
			self.mute = False
			if progress_callback == None:
				self.progress_callback = self.dummy_callback
			else:
				self.progress_callback = progress_callback
		
		def inspect_quick(self, stream):
			"""Quickly checks if stream contains DDS data, and gets the
			version, by looking at the first 8 bytes.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pass

		# overriding pyffi.object_models.FileFormat.Data methods
		def get_sized_str_entry(self, name):
			lower_name = name.lower()
			for archive in self.archives:
				for sized_str_entry in archive.sized_str_entries:
					if lower_name == sized_str_entry.lower_name:
						return sized_str_entry
			# still here - error!
			raise KeyError("Can't find a sizedstr entry for {}, not from this archive?".format(name) )
			
		def inspect(self, stream):
			"""Quickly checks if stream contains DDS data, and reads the
			header.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pos = stream.tell()
			try:
				self.inspect_quick(stream)
				self.header.read(stream, data=self)
				self.version = self.header.version
				self.flag_2 = self.header.flag_2
				self.user_version = self.header.flag_2
			finally:
				stream.seek(pos)
		
		def arr_2_str(self, arr):
			return b"".join(b for b in arr)
		
		def read_z_str(self, stream, pos):
			"""get a zero terminated string from stream at pos """
			stream.seek( pos )
			z_str = OvlFormat.ZString()
			z_str.read(stream, data=self)
			return str(z_str)
		
		# dummy (black hole) callback for if we decide we don't want one
		def dummy_callback(self, *args, **kwargs):
			return
		
		def print_and_callback(self, message, value=None, max=None):
			# don't print the message if it is identical to the last one - it
			# will slow down massively repetitive tasks
			if self.last_print != message:
				print(message)
				self.last_print = message
			
			# call the callback
			if not self.mute:
				self.progress_callback(message, value, max)
		
		def read(self, stream, verbose=0, file="", commands=[], mute=False):
			"""Read a dds file.

			:param stream: The stream from which to read.
			:type stream: ``file``
			"""
			# store commands
			self.commands = commands
			self.mute = mute
			# store file name for later
			if file:
				self.file = file
				self.dir, self.basename = os.path.split(file)
				self.file_no_ext = os.path.splitext(self.file)[0]
			
			self.archives = []
			
			# read the file
			self.header.read(stream, data=self)
			self.version = self.header.version
			self.flag_2 = self.header.flag_2
			self.user_version = self.header.flag_2
			# eoh = stream.tell()
			print(self.header)
			
			# maps OVL hash to final filename + extension
			self.name_hashdict = {}
			# for PZ names
			self.name_list = []
			
			# get the name table, names are separated by 0x00 but are always gotten by array index
			names = self.arr_2_str(self.header.names)
			names_reader = io.BytesIO(names)
			
			archive_names = self.arr_2_str(self.header.archive_names)
			archive_names_reader = io.BytesIO(archive_names)
			
			# for dev purposes so we can populate the file type enum in ovl.xml
			# hash_enums = set()
			
			# add extensions to hash dict
			hm_max = len(self.header.mimes)
			for hm_index, mime_entry in enumerate(self.header.mimes):
				self.print_and_callback("Adding extensions to hash dict", value=hm_index, max=hm_max)
				# get the whole mime type string
				mime_type = self.read_z_str(names_reader, mime_entry.offset)
				# only get the extension
				mime_entry.ext = mime_type.split(":")[-1]
				# the stored mime hash is not used anywhere
				self.name_hashdict[mime_entry.mime_hash] = mime_type
				# instead we must calculate the DJB hash of the extension and store that
				# because this is how we find the extension from inside the archive
				self.name_hashdict[djb(mime_entry.ext)] = mime_entry.ext
				
				# for dev purposes only
				# hash_option = (mime_type, '<option value="'+str(mime_entry.mime_hash)+'" name="'+mime_type+'"></option>')
				# hash_enums.add(hash_option)
			# # for development of xml hash enum
			# for mime, xml_str in sorted(hash_enums):
				# print(xml_str)
			
			# add file name to hash dict; ignoring the extension pointer
			hf_max = len(self.header.files)
			for hf_index, file_entry in enumerate(self.header.files):
				self.print_and_callback("Adding file names to hash dict", value=hf_index, max=hf_max)
				# get file name from name table
				file_name = self.read_z_str(names_reader, file_entry.offset)
				self.name_hashdict[file_entry.file_hash] = file_name
				# there seems to be no need for now to link the two
				file_entry.ext = self.header.mimes[file_entry.extension].ext
				file_entry.name = file_name
				self.name_list.append(file_name)
				# print(file_name+"."+file_entry.ext , file_entry.unkn_0, file_entry.unkn_1)
			# return	
			# print(self.name_hashdict)
			
			# create directories
			hd_max = len(self.header.dirs)
			for hd_index, dir_entry in enumerate(self.header.dirs):
				self.print_and_callback("Creating directories", value=hd_index, max=hd_max)
				# get dir name from name table
				dir_name = self.read_z_str(names_reader, dir_entry.offset)
				# fix up the name
				dir = os.path.normpath(os.path.join(os.getcwd(), dir_name.lstrip("..\\")) )
				# create dir, do nothing if it already exists
				# os.makedirs(dir, exist_ok=True)
				# print(dir)
			
			# get names of all texture assets
			ht_max = len(self.header.textures)
			ht_index = 0
			for texture_entry in self.header.textures:
				self.print_and_callback("Getting texture asset names", value = ht_index, max = ht_max)
				ht_index += 1
				# nb. 4 unknowns per texture
				try:
					texture_entry.name = self.name_hashdict[texture_entry.file_hash]
				except:
					# this seems to happen for main.ovl - external textures?
					texture_entry.name = "bad hash"
				# print(name, texture_entry.unknown_1, texture_entry.unknown_2, texture_entry.unknown_3, texture_entry.unknown_4, texture_entry.unknown_5, texture_entry.unknown_6)#, texture_entry.unknown_7)
				
			# print(sorted(set([t.unknown_6 for t in self.header.textures])))
			# print(textures)
			ovs_dict = {}
			ha_max = len(self.header.archives)
			for archive_i, archive_entry in enumerate(self.header.archives):
				self.print_and_callback("Extracting archives", value=archive_i, max=ha_max)
				
				archive_entry.name = self.read_z_str(archive_names_reader, archive_entry.offset)
				self.print_and_callback(f"Reading archive {archive_entry.name}")
				# skip archives that are empty
				if archive_entry.compressed_size == 0:
					print("archive is empty")
					continue
				# those point to external ovs archives
				if archive_i > 0:
					# JWE style
					if self.flag_2 == 24724:
						archive_entry.ovs_path = self.file_no_ext+".ovs."+archive_entry.name.lower()
					# PZ Style
					elif self.flag_2 == 8340:
						archive_entry.ovs_path = self.file_no_ext+".ovs"
					else:
						print("unsupported flag_2", self.flag_2)
						return
					# print(archive_entry.ovs_path)
					# make sure that the ovs exists
					if not os.path.exists(archive_entry.ovs_path):
						raise FileNotFoundError("OVS file not found. Make sure is is here: \n"+archive_entry.ovs_path)
					# gotta keep them open because more than one archive can live in one ovs file eg PZ inspector
					if archive_entry.ovs_path not in ovs_dict:
						ovs_dict[archive_entry.ovs_path] = open(archive_entry.ovs_path, 'rb')
					
					# todo: account for OVS offsets specified in archive_entry
					# todo: footer bytes in OVS?
					self.unzip(ovs_dict[archive_entry.ovs_path], archive_entry, archive_i, save_temp_dat = self.file+"_"+archive_entry.name+".dat")
				else:
					start_pos = stream.tell()
					# seek from eof backwards to zlib
					stream.seek(-archive_entry.compressed_size, 2)
					# see if we ended up at the same position
					if start_pos != stream.tell():
						print("Undecoded data after header, adjusted cursor")
						print("end of decoding",start_pos)
						print("should be at",stream.tell())
					self.unzip(stream, archive_entry, archive_i, save_temp_dat = self.file+"_"+archive_entry.name+".dat")
			
			# find texstream buffers
			tb_max = len(self.archives[0].sized_str_entries)
			for tb_index, sized_str_entry in enumerate(self.archives[0].sized_str_entries):
				self.print_and_callback("Finding texstream buffers", value=tb_index, max=tb_max)
				if sized_str_entry.ext == "tex":
					for lod_i in range(3):
						for archive in self.archives[1:]:
							for other_sizedstr in archive.sized_str_entries:
								if sized_str_entry.basename in other_sizedstr.name and "_lod"+str(lod_i) in other_sizedstr.name:
									sized_str_entry.data_entry.buffers.extend(other_sizedstr.data_entry.buffers)
								
			# postprocessing of data buffers
			for archive in self.archives:				
				for data_entry in archive.data_entries:
					# just sort buffers by their index value
					data_entry.update_buffers()
			
			# print(len(self.archives))
				
			# # we don't use context manager so gotta close them
			# for ovs_file in ovs_dict.values():
				# ovs_file.close()
				
		def unzip(self, stream, archive_entry, archive_i, save_temp_dat=""):
			zipped = stream.read(archive_entry.compressed_size)
			self.print_and_callback(f"Reading {archive_entry.name}")
			self.zlib_header = zipped[:2]
			zlib_compressed_data = zipped[2:]
			# https://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
			# we avoid the two zlib magic bytes to get our unzipped content
			zlib_data = bytearray( zlib.decompress(zlib_compressed_data, wbits = -zlib.MAX_WBITS) )
			if save_temp_dat and "write_dat" in self.commands:
				# for debugging, write deflated content to dat
				with open(save_temp_dat, 'wb') as out:
					out.write(zlib_data)
			# now read the archive stream
			
			archive = OvlFormat.Archive(self, zlib_data, archive_entry, archive_i)
			archive.read_archive( archive.stream )
			self.archives.append( archive )

		def write(self, stream, verbose=0, file_path = ""):
			"""Write a dds file.

			:param stream: The stream to which to write.
			:type stream: ``file``
			:param verbose: The level of verbosity.
			:type verbose: ``int``
			"""
			
			print("Writing OVL")
			
			exp_dir = os.path.dirname(file_path)
			ovs_dict = {}
			# compress data stream
			for i, (archive_entry, archive) in enumerate(zip(self.header.archives, self.archives)):
				# write archive into bytes IO stream
				temp_archive_writer = io.BytesIO()
				archive.write_archive(temp_archive_writer)
				# compress data
				uncompressed_bytes = temp_archive_writer.getvalue()
				compressed = zlib.compress(uncompressed_bytes)
				archive_entry.uncompressed_size = len(uncompressed_bytes)
				archive_entry.compressed_size = len(compressed)
				if i == 0:
					ovl_compressed = compressed
					archive_entry.read_start = 0
				else:
					exp_path = os.path.join(exp_dir, os.path.basename(archive_entry.ovs_path) )
					# gotta keep them open because more than one archive can live in one ovs file eg PZ inspector
					if exp_path not in ovs_dict:
						ovs_dict[exp_path] = open(exp_path, 'wb')
					
					# todo: account for OVS offsets specified in archive_entry
					# todo: footer bytes in OVS?
					ovs_stream = ovs_dict[exp_path]
					
					archive_entry.read_start = ovs_stream.tell()
					ovs_stream.write(compressed)

			print("Updating AUX sizes in OVL")
			for aux in self.header.aux_entries:
				#print(aux)
				name = self.header.files[aux.file_index].name
				if aux.extension_index != 0: 
					bnkpath = f"{self.archives[0].header.file_no_ext}_{name}_bnk_s.aux"
					
				else:
					bnkpath = f"{self.archives[0].header.file_no_ext}_{name}_bnk_b.aux"
					
				#grab and update size
				if os.path.isfile(bnkpath):
					aux.size = os.path.getsize(bnkpath)
					#print(aux.size)
			
			with open(file_path, 'wb') as ovl_stream:
				# first header
				self.header.write(ovl_stream, data=self)
				# write zlib block
				ovl_stream.write(ovl_compressed)
				
			# archive_entry = self.header.archives[0]
			# old_size = int(archive_entry.compressed_size)
			# add size of zlib header
			# new_size = # + 2
			# print("old size:",old_size)
			# print("new size:",new_size)
			# print("zlib magic",self.zlib_header)
			
			# we don't use context manager so gotta close them
			for ovs_file in ovs_dict.values():
				ovs_file.close()

	class BufferEntry:
		def read_data(self, archive):
			"""Load data from archive stream into self for modification and io"""
			self.data = archive.stream.read(self.size)

		def update_data(self, data):
			"""Set data internal data so it can be written on save and update the size value"""
			self.data = data
			self.size = len(data)
			
	class DataEntry:
		def update_data(self, datas):
			"""Load datas into this DataEntry's buffers, and update its size values according to an assumed pattern
			data : list of bytes object, each representing the data of one buffer for this data entry"""
			for buffer, data in zip(self.buffers, datas):
				buffer.update_data(data)
			# update data 0, 1 size
			total = sum( len(d) for d in datas)
			if len(datas) == 1:
				self.size_1 = len(datas[0])
				self.size_2 = 0
			elif len(datas) == 2:
				self.size_1 = 0
				self.size_2 = sum( len(d) for d in datas )
			elif len(datas) > 2:
				self.size_1 = sum( len(d) for d in datas[:-1] )
				self.size_2 = len(datas[-1])
			# print(total)
			# print(self.size_1)
			# print(self.size_2)
		
		def update_buffers(self,):
			# sort the buffer entries of each data entry by their index
			self.buffers.sort( key=lambda buffer: buffer.index )
			# trim to valid buffers (ignore ones that run out of count, usually zero-sized ones)
			# self.buffers = self.buffers[:self.buffer_count]
			# self.buffers = list(b for b in self.buffers if b.size)
			
		@property
		def buffer_datas(self):
			"""Get data for each non-empty buffer (should have been sorted before)"""
			return list(buffer.data for buffer in self.buffers if buffer.size)
	
	class HeaderPointer:
		def read_data(self, archive):
			"""Load data from archive header data readers into pointer for modification and io"""

			self.padding = b""
			if self.header_index == MAX_UINT32:
				self.data = None
			else:
				header_reader = archive.header_entries[self.header_index].data
				header_reader.seek(self.data_offset)
				self.data = header_reader.read(self.data_size)
			
		def write_data(self, archive, update_copies=False):
			"""Write data to header data, update offset, also for copies if told"""

			if self.header_index == MAX_UINT32:
				pass
			else:
				# get header data to write into
				writer = archive.header_entries[self.header_index].data
				# update data offset
				self.data_offset = writer.tell()
				if update_copies:
					for other_pointer in self.copies:
						other_pointer.data_offset = writer.tell()
				# write data to io, adjusting the cursor for that header
				writer.write(self.data + self.padding)

		def strip_zstring_padding(self):
			"""Move surplus padding into the padding attribute"""
			# the actual zstring content + end byte
			data = self.data.split(b"\x00")[0]+b"\x00"
			# do the split itself
			self.split_data_padding( len(data) )
			
		def split_data_padding(self, cut):
			"""Move a fixed surplus padding into the padding attribute"""
			_d = self.data + self.padding
			self.padding = _d[cut:]
			self.data = _d[:cut]
		
		def link_to_header(self, archive):
			"""Store this pointer in suitable header entry"""

			if self.header_index == MAX_UINT32:
				pass
			else:
				# get header entry
				entry = archive.header_entries[self.header_index]
				if self.data_offset not in entry.pointer_map:
					entry.pointer_map[self.data_offset] = []
				entry.pointer_map[self.data_offset].append(self)

		def update_data(self, data, update_copies=False, pad_to=None, include_old_pad=False):
			"""Update data and size of this pointer"""
			self.data = data
			# only change padding if a new alignment is given
			if pad_to:
				len_d = len(data)
				# consider the old padding for alignment?
				if include_old_pad:
					len_d += len(self.padding)
				moduloed = len_d % pad_to
				if moduloed:
					# create the new blank padding
					new_pad = b"\x00" * (pad_to - moduloed)
				else:
					new_pad = b""
				# append new to the old padding
				if include_old_pad:
					self.padding = self.padding + new_pad
				# overwrite the old padding
				else:
					self.padding = new_pad
			self.data_size = len(self.data + self.padding)
			# update other pointers if asked to by the injector
			if update_copies:
				for other_pointer in self.copies:
					if other_pointer is not self:
						other_pointer.update_data(data, pad_to=pad_to, include_old_pad=include_old_pad)
			
		def get_reader(self):
			"""Returns a reader of its data"""
			return io.BytesIO(self.data)

		def read_as(self, pyffi_cls, data, num=1):
			"""Return self.data as pyffi cls
			Data must be an object that has version & user_version attributes"""
			reader = self.get_reader()
			insts = []
			for i in range(num):
				inst = pyffi_cls()
				inst.read(reader, data=data)
				insts.append(inst)
			return insts

	class Archive(pyffi.object_models.FileFormat.Data):
		"""A class to contain the actual Ovl data."""
		def __init__(self, header, zlib_data, archive_entry, archive_index = 0):
			# the main ovl header
			self.header = header
			
			self.zlib_data = zlib_data
			# just to get read() api on bytes object
			self.stream = io.BytesIO(zlib_data)
			self.archive_entry = archive_entry
			self.archive_index = archive_index
			self.version = self.header.version
			self.user_version = self.header.user_version

		def indir(self, name):
			return os.path.join( self.dir, name)
			
		def get_name(self, entry):
			"""Fetch a filename from hash dict"""
			# JWE style
			if self.header.flag_2 == 24724:
				# print("JWE ids",entry.file_hash, entry.ext_hash)
				try:
					n = self.header.name_hashdict[entry.file_hash]
				except:
					n = "NONAME"
				try:
					e = self.header.name_hashdict[entry.ext_hash]
				except:
					e = "UNKNOWN"
			# PZ Style
			elif self.header.flag_2 == 8340:
				# print("PZ ids",entry.file_hash, entry.ext_hash)
				try:
					n = self.header.name_list[entry.file_hash]
				except:
					n = "NONAME"
				try:
					e = self.header.name_hashdict[entry.ext_hash]
				except:
					e = "UNKNOWN"
			return n + "." + e
		
		def write_archive(self, stream):

			for i, header_entry in enumerate(self.header_entries):
				# maintain sorting order
				# grab the first pointer for each address
				# it is assumed that subsequent pointers to that address share the same data
				sorted_first_pointers = [pointers[0] for offset, pointers in sorted(header_entry.pointer_map.items()) ]
				if sorted_first_pointers:
					# only known from indominus
					first_offset = sorted_first_pointers[0].data_offset
					if first_offset != 0:
						print(f"Found {first_offset} unaccounted bytes at start of header data {i}")
						unaccounted_bytes = header_entry.data.getvalue()[:first_offset]
					else:
						unaccounted_bytes = b""

					# clear io objects
					header_entry.data = io.BytesIO()
					header_entry.data.write(unaccounted_bytes)
					# write updated strings
					for pointer in sorted_first_pointers:
						pointer.write_data(self, update_copies=True)
				else:
					print(f"No pointers into header entry {i} - keeping its stock data!")

			# do this first so header entries can be updated
			header_data_writer = io.BytesIO()
			# the ugly stuff with all fragments and sizedstr entries
			for header_entry in self.header_entries:
				header_data_bytes = header_entry.data.getvalue()
				# JWE style
				if self.header.flag_2 == 24724:
					header_entry.offset = header_data_writer.tell()
				# PZ Style
				elif self.header.flag_2 == 8340:
					header_entry.offset = self.archive_entry.ovs_header_offset + header_data_writer.tell()
				header_entry.size = len(header_data_bytes)
				header_data_writer.write( header_data_bytes )
			
			# write out all entries
			for l in (self.header_types, self.header_entries, self.data_entries, 
					  self.buffer_entries, self.sized_str_entries, self.fragments):
				for entry in l:
					entry.write(stream, self)
			# write set & asset stuff
			self.set_header.write(stream, self)
			# write the header data containing all the pointers' datas
			stream.write( header_data_writer.getvalue() )
			
			# write buffer data
			for b in self.buffers_io_order:
				stream.write(b.data)
				
			# do some calculations
			# self.archive_entry.uncompressed_size = stream.tell()
			# self.archive_entry.uncompressed_size = self.calc_uncompressed_size()
		
		def calc_uncompressed_size(self, ):
			"""Calculate the size of the whole decompressed stream for this archive"""
			
			# TODO: this is apparently wrong during write_archive, as if something wasn't properly updated
			
			check_data_size_1 = 0
			check_data_size_2 = 0
			for data_entry in self.data_entries:
				check_data_size_1 += data_entry.size_1
				check_data_size_2 += data_entry.size_2
			return self.header_size + self.calc_header_data_size() + check_data_size_1 + check_data_size_2
			
		def calc_header_data_size(self, ):
			"""Calculate the size of the whole data entry region that sizedstr and fragment entries point into"""
			return sum( header_entry.size for header_entry in self.header_entries )
			
		def read_archive(self, stream):
			"""Reads a deflated archive stream"""
			
			# read the entries in archive order
			self.read_header_types()
			self.read_header_entries()
			self.read_data_entries()
			self.read_buffer_entries()
			self.read_sizedstr_entries()
			self.read_fragment_entries()

			set_data_offset = stream.tell()
			print("Set header address", set_data_offset)
			self.read_sets_assets()
			self.map_assets()
	
			# size check again
			self.header_size = stream.tell()
			set_data_size = self.header_size - set_data_offset
			if set_data_size != self.archive_entry.set_data_size:
				raise AttributeError("Set data size incorrect (got {}, expected {})!".format(set_data_size, self.archive_entry.set_data_size) )
			
			# another integrity check
			if self.calc_uncompressed_size() != self.archive_entry.uncompressed_size:
				raise AttributeError("Archive.uncompressed_size ({}) does not match calculated size ({})".format(self.archive_entry.uncompressed_size, self.calc_uncompressed_size()))
			
			# go back to header offset
			stream.seek(self.header_size)
			# add IO object to every header_entry
			for header_entry in self.header_entries:
				header_entry.data = io.BytesIO( stream.read(header_entry.size) )
			
			self.check_header_data_size = self.calc_header_data_size()
			self.map_pointers()
			self.calc_pointer_addresses()
			self.calc_pointer_sizes()
			self.populate_pointers()
			
			self.map_frags()
			self.map_buffers()
			
			if "write_frag_log" in self.header.commands:
				self.write_frag_log()
		
		def read_header_types(self):
			"""Reads a HeaderType struct for the count"""
			self.header_types = [OvlFormat.HeaderType() for x in range(self.archive_entry.num_header_types)]
			# for checks
			check_header_types = 0

			# read header types
			print("Header Types", len(self.header_types))
			for header_type in self.header_types:
				header_type.read(self.stream, self)
				# add this header_type's count to check var
				check_header_types += header_type.num_headers
				# print(header_type)
			
			# ensure that the sum equals the value specified by the archive_entry
			if check_header_types != self.archive_entry.num_headers:
				raise AttributeError("Mismatch between total amount of headers")

		def read_header_entries(self):
			self.header_entries = []
			# # a dict keyed with header type hashes 
			# headers_by_type = {}
			# read all header entries			
			for header_type in self.header_types:
				for i in range(header_type.num_headers):					
					self.header.print_and_callback(f"Reading header entries - type {header_type.type}", value=i, max=header_type.num_headers)
					header_entry = OvlFormat.HeaderEntry()
					header_entry.read(self.stream, self)
					header_entry.header_type = header_type
					header_entry.type = header_type.type
					self.header_entries.append(header_entry)
					# print(header_entry)
					header_entry.name = self.get_name(header_entry)
					header_entry.basename, header_entry.ext = os.path.splitext(header_entry.name)
					header_entry.ext = header_entry.ext[1:]
					# store fragments per header for faster lookup
					header_entry.fragments = []				
					
					#print("header",header_entry.name)
					#print("size",header_entry.size)
					# print("num_files", header_entry.num_files)
					# print("header",header_entry)
					
					# todo: can we make use of this again for an improved fragment getter?
					# # create list if required
					# ext_hash = header_entry.ext_hash
					# if ext_hash not in headers_by_type:
						# headers_by_type[ext_hash] = []
					# # append this header so we can access by type & index per type
					# headers_by_type[ext_hash].append(header_entry)

		def read_data_entries(self):
			self.data_entries = [OvlFormat.DataEntry() for i in range(self.archive_entry.num_datas)]
			check_buffer_count = 0
			# read all data entries
			print("Data Entries", len(self.data_entries))
			de_max = len(self.data_entries)
			for de_index, data_entry in enumerate(self.data_entries):
				self.header.print_and_callback("Reading data entries", value=de_index, max=de_max)
				data_entry.read(self.stream, self)
				check_buffer_count += data_entry.buffer_count
				data_entry.name = self.get_name(data_entry)
				
			if check_buffer_count != self.archive_entry.num_buffers:
				raise AttributeError("Wrong buffer count (expected "+str(self.archive_entry.num_buffers)+")!")

		def read_buffer_entries(self):
			self.buffer_entries = [OvlFormat.BufferEntry() for i in range(self.archive_entry.num_buffers)]
			print("Buffer Entries", len(self.buffer_entries))
			# read all Buffer entries
			be_max = len(self.buffer_entries)
			for be_index, buffer_entry in enumerate(self.buffer_entries):
				self.header.print_and_callback("Reading buffer entries", value=be_index, max=be_max)
				buffer_entry.read(self.stream, self)

		def read_sizedstr_entries(self):
			self.sized_str_entries = [OvlFormat.SizedStringEntry() for i in range(self.archive_entry.num_files)]
			print("SizedString Entries")
			# read all file entries type b
			ss_max = len(self.sized_str_entries)
			for ss_index, sized_str_entry in enumerate(self.sized_str_entries):
				self.header.print_and_callback("Reading sizedstr entries", value=ss_index, max=ss_max)
				sized_str_entry.read(self.stream, self)
				sized_str_entry.name = self.get_name(sized_str_entry)
				sized_str_entry.lower_name = sized_str_entry.name.lower()
				sized_str_entry.basename, ext = os.path.splitext(sized_str_entry.name)
				sized_str_entry.ext = ext[1:]
				sized_str_entry.children = []
				sized_str_entry.parent = None
				sized_str_entry.fragments = []
				sized_str_entry.model_data_frags = []
				sized_str_entry.model_count = 0
				# get data entry for link to buffers, or none
				sized_str_entry.data_entry = self.find_entry(self.data_entries, sized_str_entry.file_hash, sized_str_entry.ext_hash)
				# print("\nSizedString",sized_str_entry.name,sized_str_entry.pointers[0].data_offset,sized_str_entry.header_index)#2476
			print("Num SizedString Entries",len(self.sized_str_entries))

		def read_fragment_entries(self):
			self.fragments = [OvlFormat.Fragment() for i in range(self.archive_entry.num_fragments)]
			print("Fragment Entries")
			# read all self.fragments
			fr_max = len(self.fragments)
			for fr_index, fragment in enumerate(self.fragments):
				self.header.print_and_callback("Reading fragment entries", value=fr_index, max=fr_max)
				fragment.read(self.stream, self)
				# we assign these later
				fragment.done = False
				fragment.lod = False
				fragment.name = None
			print("Num Fragment Entries",len(self.fragments))

		def read_sets_assets(self):
			"""Read the set header block that defines sets and assets"""
			print("Reading sets and assets...")
			self.set_header = OvlFormat.SetHeader()
			self.set_header.read(self.stream, self)
			print("Num Sets",len(self.set_header.sets))
			print("Num Assets",len(self.set_header.assets))
			# print(self.set_header)
			# signature check
			if not (self.set_header.sig_a == 1065336831 and self.set_header.sig_b == 16909320):
				raise AttributeError("Set header signature check failed!")
			# print("Set Entries")
			# read all set entries
			se_max = len(self.set_header.sets)
			for se_index, set_entry in enumerate(self.set_header.sets):
				self.header.print_and_callback("Reading sets", value=se_index, max=se_max)
				set_entry.name = self.get_name(set_entry)
				set_entry.entry = self.find_entry(self.sized_str_entries, set_entry.file_hash, set_entry.ext_hash)
				
			ae_max = len(self.set_header.assets)
			for ae_index, asset_entry in enumerate(self.set_header.assets):
				self.header.print_and_callback("Reading assets", value=ae_index, max=ae_max)
				asset_entry.name = self.get_name(asset_entry)
				asset_entry.entry = self.sized_str_entries[asset_entry.file_index]
			
		def calc_pointer_addresses(self):
			print("Calculating pointer addresses")
			# store absolute read addresses from the start of file
			for entry in itertools.chain(self.fragments, self.sized_str_entries):
				# for access from start of file
				for pointer in entry.pointers:
					# some have max_uint as a header value, what do they refer to
					if pointer.header_index == MAX_UINT32:
						# print("Warning: {} has no header index (-1)".format(entry.name))
						pointer.header = 9999999
						pointer.type = 9999999
						pointer.address = 9999999
						# sized_str_entry.parent 
					else:
						pointer.header = self.header_entries[pointer.header_index]
						# store type number of each header entry
						pointer.type = pointer.header.type
						pointer.address = self.header_size + pointer.header.offset + pointer.data_offset
			
		def calc_pointer_sizes(self):
			"""Assign an estimated size to every pointer"""
			print("calculating pointer sizes")
			# calculate pointer data sizes
			for entry in self.header_entries:
				# make them unique and sort them
				sorted_items = sorted( entry.pointer_map.items() )
				# add the end of the header data block
				sorted_items.append( (entry.size, None) )
				# get the size of each fragment: find the next entry's address and substract it from address
				for i, (offset, pointers) in enumerate(sorted_items[:-1]):
					# get the offset of the next entry that points into this buffer, substract this offset
					data_size = sorted_items[i+1][0] - offset
					for pointer in pointers:
						pointer.data_size = data_size

		def map_pointers(self):
			"""Assign list of copies to every pointer so they can be updated with the same data easily"""
			print("\nMapping pointers")
			# reset pointer map for each header entry
			for header_entry in self.header_entries:
				header_entry.pointer_map = {}
			print("\nLinking pointers to header")
			# append all valid pointers to their respective dicts
			for entry in itertools.chain(self.fragments, self.sized_str_entries):
				for pointer in entry.pointers:
					pointer.link_to_header(self)
			print("\nFinding duplicate pointers")
			for header_entry in self.header_entries:
				# for every pointer, store any other pointer that points to the same address
				for offset, pointers in header_entry.pointer_map.items():
					for p in pointers:
						# p.copies = [po for po in pointers if po != p]
						p.copies = pointers
		
		def populate_pointers(self):
			"""Load data for every pointer"""
			print("Reading data into pointers")
			for entry in itertools.chain(self.fragments, self.sized_str_entries):
				for pointer in entry.pointers:
					pointer.read_data(self)
			
		def map_assets(self):
			"""Store start and stop indices to asset entries, translate hierarchy to sizedstr entries"""
			# store start and stop asset indices
			for i, set_entry in enumerate(self.set_header.sets):
				# for the last entry
				if i == self.set_header.set_count-1:
					set_entry.end = self.set_header.asset_count
				# store start of the next one as this one's end
				else:
					set_entry.end = self.set_header.sets[i+1].start
				# map assets to entry
				set_entry.assets = self.set_header.assets[set_entry.start : set_entry.end]
				# print("SET:",set_entry.name)
				# print("ASSETS:",[a.name for a in set_entry.assets])
				# store the references on the corresponding sized str entry
				set_entry.entry.children = [self.sized_str_entries[a.file_index] for a in set_entry.assets]
				for child in set_entry.entry.children:
					child.parent = set_entry.entry

		def frags_from_pointer(self, p, count):
			frags = self.frags_for_pointer(p)
			return self.get_frags_after_count(frags, p.address, count)

		def frags_for_pointer(self, p):
			return self.header_entries[p.header_index].fragments

		def collect_matcol(self, ss_entry):
			print("\nMATCOL:",ss_entry.name)

			# Sized string initpos = position of first fragment for matcol
			# input_frags = self.frags_for_pointer(ss_entry.pointers[0])
			# ss_entry.fragments = self.get_frag_after(input_frags, ((4,4),), ss_entry.pointers[0].address)
			ss_entry.fragments = self.frags_from_pointer(ss_entry.pointers[0], 1)
			ss_entry.f0 = ss_entry.fragments[0]
			
			# print(ss_entry.f0)
			#0,0,collection count,0
			f0_d0 = struct.unpack("<4I", ss_entry.f0.pointers[0].data)
			#flag (3=variant, 2=layered) , 0
			ss_entry.has_texture_list_frag = len(ss_entry.f0.pointers[1].data) == 8
			if ss_entry.has_texture_list_frag:
				f0_d1 = struct.unpack("<2I", ss_entry.f0.pointers[1].data)
			else:
				f0_d1 = struct.unpack("<6I", ss_entry.f0.pointers[1].data)
			# print("f0_d0", f0_d0)
			# print("f0_d1", f0_d1)
			ss_entry.is_variant = f0_d1[0] == 3
			ss_entry.is_layered = f0_d1[0] == 2
			# print("has_texture_list_frag",ss_entry.has_texture_list_frag)
			# print("is_variant",ss_entry.is_variant)
			# print("is_layered",ss_entry.is_layered)
			# print(ss_entry.tex_pointer)
			if ss_entry.has_texture_list_frag:
				# input_frags = self.frags_for_pointer(ss_entry.f0.pointers[1])
				# ss_entry.tex_pointer = self.get_frag_after(input_frags, ((4,4),), ss_entry.f0.pointers[1].address)[0]
				ss_entry.tex_pointer = self.frags_from_pointer(ss_entry.f0.pointers[1], 1)[0]
				tex_pointer_d0 = struct.unpack("<4I", ss_entry.tex_pointer.pointers[0].data)
				# print("tex_pointer_d0", tex_pointer_d0)
				tex_count = tex_pointer_d0[2]
				# print("tex_count",tex_count)
				ss_entry.tex_frags = self.frags_from_pointer(ss_entry.tex_pointer.pointers[1], tex_count*3)
				# ss_entry.tex_frags = []
				# input_frags = self.frags_for_pointer(ss_entry.tex_pointer.pointers[1])
				# for t in range(tex_count):
				# 	ss_entry.tex_frags += self.get_frag_after(input_frags, ((4,6),(4,6),(4,6)), ss_entry.tex_pointer.pointers[1].address)
				# for tex in ss_entry.tex_frags:
				# 	print(tex.pointers[1].data)
			else:
				ss_entry.tex_pointer = None
			# material pointer frag
			ss_entry.mat_pointer = self.frags_from_pointer(ss_entry.f0.pointers[1], 1)[0]
			# ss_entry.mat_pointer_frag = self.get_frag_after(address_0_fragments, ((4,4),), ss_entry.f0.pointers[1].address)
			# ss_entry.mat_pointer = ss_entry.mat_pointer_frag[0]
			mat_pointer_d0 = struct.unpack("<6I", ss_entry.mat_pointer.pointers[0].data)
			# print("mat_pointer_d0",mat_pointer_d0)
			mat_count = mat_pointer_d0[2]
			# print("mat_count",mat_count)
			ss_entry.mat_frags = []
			for t in range(mat_count):
				if ss_entry.is_variant:
					m0 = self.frags_from_pointer(ss_entry.mat_pointer.pointers[1], 1)[0]
					# m0 = self.get_frag_after(address_0_fragments, ((4,6),), ss_entry.mat_pointer.pointers[1].address)[0]
					# print(m0.pointers[1].data)
					m0.name = ss_entry.name
					ss_entry.mat_frags.append( (m0,) )
				elif ss_entry.is_layered:
					mat_frags = self.frags_from_pointer(ss_entry.mat_pointer.pointers[1], 3)
					# mat_frags = self.get_frag_after(address_0_fragments, ((4,6),(4,4),(4,4)), ss_entry.mat_pointer.pointers[1].address)

					m0, info, attrib  = mat_frags
					m0.pointers[1].strip_zstring_padding()
					# print(m0.pointers[1].data)
					
					info_d0 = struct.unpack("<8I", info.pointers[0].data)
					info_count = info_d0[2]
					# print("info_count", info_count)
					info.children = self.frags_from_pointer(info.pointers[1], info_count)
					for info_child in info.children:
						# info_child = self.get_frag_after(address_0_fragments, ((4,6),), info.pointers[1].address)[0]
						# 0,0,byte flag,byte flag,byte flag,byte flag,float,float,float,float,0
						# info_child_d0 = struct.unpack("<2I4B4fI", info_child.pointers[0].data)
						info_child.pointers[1].strip_zstring_padding()
						# print(info_child.pointers[1].data, info_d0)
					
					attrib.children = []
					attrib.pointers[0].split_data_padding(16)
					attrib_d0 = struct.unpack("<4I", attrib.pointers[0].data)
					attrib_count = attrib_d0[2]
					# print("attrib_count",attrib_count)
					attrib.children = self.frags_from_pointer(attrib.pointers[1], attrib_count)
					for attr_child in attrib.children:
						# attr_child = self.get_frag_after(address_0_fragments, ((4,6),), attrib.pointers[1].address)[0]
						# attrib.children.append(attr_child)
						# attr_child_d0 = struct.unpack("<2I4BI", attr_child.pointers[0].data)
						attr_child.pointers[1].strip_zstring_padding()
						# print(attr_child.pointers[1].data, attr_child_d0)
					
					# store names for frag log
					for frag in mat_frags + info.children + attrib.children:
						frag.name = ss_entry.name
					# store frags
					ss_entry.mat_frags.append( mat_frags )
			if ss_entry.has_texture_list_frag:
				for frag in ss_entry.tex_frags + [ss_entry.tex_pointer,]:
					frag.name = ss_entry.name
			all_frags = [ss_entry.f0, ss_entry.mat_pointer]
			for frag in all_frags:
				frag.name = ss_entry.name
					
		def collect_mdl2(self, mdl2_sized_str_entry, model_info, mdl2_pointer):
			#print("Collecting model fragments for", mdl2_sized_str_entry.name)
			mdl2_sized_str_entry.fragments = self.frags_from_pointer(mdl2_pointer, 5)
			mdl2_sized_str_entry.model_info = model_info
			mdl2_sized_str_entry.model_count = model_info.model_count
			lod_pointer = mdl2_sized_str_entry.fragments[3].pointers[1]
			# remove padding from materials1 fragment
			mdl2_sized_str_entry.fragments[2].pointers[1].split_data_padding(4*model_info.mat_1_count)

			# get and set fragments
			#print("Num model data frags",mdl2_sized_str_entry.model_count)
			mdl2_sized_str_entry.model_data_frags = self.frags_from_pointer(lod_pointer, mdl2_sized_str_entry.model_count)

		def map_frags(self):
			print("\nMapping SizedStrs to Fragments")

			# we go from the start
			address_0_fragments = list(sorted(self.fragments, key=lambda f: f.pointers[0].address))

			# just reverse is good enough, no longer need to sort them
			sorted_sized_str_entries = list(reversed(self.sized_str_entries))
			for frag in address_0_fragments:
				# header_index = frag.pointers[0].header_index
				# print(header_index, header_index != MAX_UINT32)
				# fragments always have a validheader index
				self.header_entries[frag.pointers[0].header_index].fragments.append(frag)

			# todo: document more of these type requirements
			dic = { "ms2": 3,
					"bani": 1,
					"tex": 2,
					"xmlconfig": 1,
					# "enumnamer": ( (4,4), ),
					# "motiongraphvars": ( (4,4), (4,6), (4,6), (4,6), (4,6), (4,6), (4,6), (4,6), ),
					# "hier": ( (4,6) for x in range(19) ),
					"spl": 1,
					"lua": 1,
					"assetpkg": 1,
					"userinterfaceicondata": 2,
					#"world": will be a variable length one with a 4,4; 4,6; then another variable length 4,6 set : set world before assetpkg in order
			}
			ss_max = len(sorted_sized_str_entries)
			for ss_index, sized_str_entry in enumerate(sorted_sized_str_entries):
				self.header.print_and_callback("Collecting fragments", value=ss_index, max=ss_max)
				# get fixed fragments
				#print("Collecting fragments for",sized_str_entry.name, sized_str_entry.pointers[0].address)
				hi = sized_str_entry.pointers[0].header_index
				if hi != MAX_UINT32:
					frags = self.header_entries[hi].fragments
				else:
					frags = address_0_fragments
				if sized_str_entry.ext in dic:

					t = dic[sized_str_entry.ext]
					# get and set fragments
					sized_str_entry.fragments = self.get_frags_after_count(frags, sized_str_entry.pointers[0].address, t)

				elif sized_str_entry.ext == "fgm":
					sized_str_entry.fragments = self.get_frag_after_terminator(frags, sized_str_entry.pointers[0].address)
				
				elif sized_str_entry.ext == "materialcollection":
					self.collect_matcol(sized_str_entry)
				# print("sizedstr",sized_str_entry.pointers[0].header_index)
				# print("frags",tuple((f.pointers[0].header_index, f.pointers[1].header_index) for f in sized_str_entry.fragments))
				# for f in sized_str_entry.fragments:
				# 	assert(f.pointers[0].header_index == sized_str_entry.pointers[0].header_index)
			# second pass: collect model fragments
			# assign the mdl2 frags to their sized str entry
			for set_entry in self.set_header.sets:
				set_sized_str_entry = set_entry.entry
				if set_sized_str_entry.ext == "ms2":
					f_1 = set_sized_str_entry.fragments[1]
					print("F-1:",f_1)
					self.write_frag_log()
					next_model_info = f_1.pointers[1].read_as(Ms2Format.CoreModelInfo, self.header)[0]
					print("next model info:",next_model_info)
					for asset_entry in set_entry.assets:
						assert(asset_entry.name == asset_entry.entry.name)
						sized_str_entry = asset_entry.entry
						if sized_str_entry.ext == "mdl2":
							self.collect_mdl2(sized_str_entry, next_model_info, f_1.pointers[1])
							pink = sized_str_entry.fragments[4]
							if (self.header.flag_2 == 24724 and pink.pointers[0].data_size == 144) \
							or (self.header.flag_2 == 8340  and pink.pointers[0].data_size == 160):
								next_model_info = pink.pointers[0].read_as(Ms2Format.Mdl2ModelInfo, self.header)[0].info
							
			# # for debugging only:
			for sized_str_entry in sorted_sized_str_entries:
				for frag in sized_str_entry.model_data_frags + sized_str_entry.fragments:
					frag.name = sized_str_entry.name
							
			# for header_i, header_entry in enumerate(self.header_entries):
				# print("Header {} with unknown count {}".format(header_i, header_entry.num_files))
		
		def map_buffers(self):
			"""Map buffers to data entries, sort buffers into load order, populate buffers with data"""
			print("\nMapping buffers")

			# this holds the buffers in the order they are read from the file
			self.buffers_io_order = []
			
			# sequentially attach buffers to data entries by each entry's buffer count
			buff_ind = 0
			for i, data in enumerate(self.data_entries):
				data.buffers = []
				for j in range(data.buffer_count):
					# print("data",i,"buffer",j, "buff_ind",buff_ind)
					buffer = self.buffer_entries[buff_ind]
					# also give each buffer a reference to data so we can access it later
					buffer.data_entry = data
					data.buffers.append(buffer)
					buff_ind +=1
			
			# only do this if there are any data entries so that max() doesn't choke 
			if self.data_entries:
				# check how many buffers occur at max in one data block
				max_buffers_per_data = max([data.buffer_count for data in self.data_entries])
				# first read the first buffer for every file
				# then the second if it has any
				# and so on, until there is no data entry left with unprocessed buffers
				for i in range(max_buffers_per_data):
					for data in self.data_entries:
						if i < data.buffer_count:
							self.buffers_io_order.append(data.buffers[i])

			# finally, we have the buffers in the correct sorting so we can read their contents
			print("\nReading from buffers")
			self.stream.seek(self.header_size + self.check_header_data_size)
			for buffer in self.buffers_io_order:
				# read buffer data and store it in buffer object
				buffer.read_data(self)
		
		def write_frag_log(self,):
			# # this is just for developing to see which unique attributes occur across a list of entries
			# ext_hashes = sorted(set([f.offset for f in self.header.files]))
			# print(ext_hashes)
			# # this is just for developing to see which unique attributes occur across a list of entries
			# ext_hashes = sorted(set([f.size for f in self.fragments]))
			# print(ext_hashes)
			self.dir = os.getcwd()
			# # for development; collect info about fragment types			
			frag_log = "self.fragments > sizedstr\nfragments in file order"
			for i, frag in enumerate(sorted(self.fragments, key=lambda f: f.pointers[0].address)):
				# #frag_log+="\n\nFragment nr "+str(i)
				# #frag_log+="\nHeader types "+str(f.type_0)+" "+str(f.type_1)
				# #frag_log+="\nEntry "+str(f.header_index_0)+" "+str(f.data_offset_0)+" "+str(f.header_index_1)+" "+str(f.data_offset_1)
				# #frag_log+="\nSized str "+str(f.sized_str_entry_index)+" "+str(f.name)
				frag_log+= "\n"+str(i)+" "+str(frag.pointers[0].address)+" "+str(frag.pointers[0].data_size)+" "+str(frag.pointers[1].address)+" "+str(frag.pointers[1].data_size)+" "+str(frag.name)+" "+str(frag.pointers[0].type)+" "+str(frag.pointers[1].type)
			with open(self.indir("frag"+str(self.archive_index)+".log"), "w") as f:
				f.write(frag_log)

		@staticmethod
		def get_frag_after_terminator(l, initpos, terminator=24):
			"""Returns entries of l matching h_types that have not been processed until it reaches a frag of terminator size."""
			out = []
			# print("looking for",h_types)
			for f in l:
				# can't add self.fragments that have already been added elsewhere
				if f.done:
					continue
				if f.pointers[0].address >= initpos:
					# print(f.data_offset_0,"  ",initpos)
					f.done = True
					out.append(f)
					if f.pointers[0].data_size == terminator:
						break
			else:
				raise AttributeError(f"Could not find a terminator fragment matching header types {h_types} and pointer[0].size {terminator}" )
			return out

		@staticmethod
		def get_frags_after_count(frags, initpos, count):
			"""Returns count entries of frags that have not been processed and occur after initpos."""
			out = []
			for f in frags:
				# check length of fragment, grab good ones
				if len(out) == count:
					break
				# can't add fragments that have already been added elsewhere
				if f.done:
					continue
				if f.pointers[0].address >= initpos:
					f.done = True
					out.append(f)
			else:
				if len(out) != count:
					raise AttributeError(f"Could not find {count} fragments after initpos {initpos}, only found {len(out)}!")
			return out

		@staticmethod
		def find_entry(l, file_hash, ext_hash):
			""" returns entry from list l whose file hash matches hash, or none"""
			# try to find it
			for entry in l:
				if entry.file_hash == file_hash and entry.ext_hash == ext_hash:
					return entry
