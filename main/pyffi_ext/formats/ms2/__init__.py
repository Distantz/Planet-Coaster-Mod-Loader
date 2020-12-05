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

import struct
import os
import re
import io
import math
import time
import numpy as np

import pyffi.object_models.xml
import pyffi.object_models.common
import pyffi.object_models

def findall(p, s):
	'''Yields all the positions of
	the pattern p in the string s.'''
	i = s.find(p)
	while i != -1:
		yield i
		i = s.find(p, i+1)
		
class Ms2Format(pyffi.object_models.xml.FileFormat):
	"""This class implements the Ms2 format."""
	xml_file_name = 'ms2.xml'
	# where to look for ms2.xml and in what order:
	# MS2XMLPATH env var, or Ms2Format module directory
	xml_file_path = [os.getenv('MS2XMLPATH'), os.path.dirname(__file__)]
	# file name regular expression match
	RE_FILENAME = re.compile(r'^.*\.ms2$', re.IGNORECASE)
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
	SizedString = pyffi.object_models.common.SizedString
	ZString = pyffi.object_models.common.ZString

	class Vector3:
		def __str__(self):
			return "[ %6.3f %6.3f %6.3f ]"%(self.x, self.y, self.z)

	class Vector4:
		def __str__(self):
			return "[ %6.3f %6.3f %6.3f %6.3f ]"%(self.x, self.y, self.z, self.w)

	class Matrix33:
		def __str__(self):
			return (
					"[ %6.3f %6.3f %6.3f ]\n"
					"[ %6.3f %6.3f %6.3f ]\n"
					"[ %6.3f %6.3f %6.3f ]\n"
					% (self.m_11, self.m_12, self.m_13, self.m_21, self.m_22, self.m_23, self.m_31, self.m_32, self.m_33))

	class Matrix44:
		def __str__(self):
			return f"{self.__class__} instance at {id(self):02x}\n" \
					f"\t[{self.m_11:7.3f} {self.m_12:7.3f} {self.m_13:7.3f} {self.m_14:7.3f}]\n" \
					f"\t[{self.m_21:7.3f} {self.m_22:7.3f} {self.m_23:7.3f} {self.m_24:7.3f}]\n" \
					f"\t[{self.m_31:7.3f} {self.m_32:7.3f} {self.m_33:7.3f} {self.m_34:7.3f}]\n" \
					f"\t[{self.m_41:7.3f} {self.m_42:7.3f} {self.m_43:7.3f} {self.m_44:7.3f}]"

		def as_list(self):
			"""Return matrix as 4x4 list."""
			return [
				[self.m_11, self.m_12, self.m_13, self.m_14],
				[self.m_21, self.m_22, self.m_23, self.m_24],
				[self.m_31, self.m_32, self.m_33, self.m_34],
				[self.m_41, self.m_42, self.m_43, self.m_44]
				]

		def as_tuple(self):
			"""Return matrix as 4x4 tuple."""
			return (
				(self.m_11, self.m_12, self.m_13, self.m_14),
				(self.m_21, self.m_22, self.m_23, self.m_24),
				(self.m_31, self.m_32, self.m_33, self.m_34),
				(self.m_41, self.m_42, self.m_43, self.m_44)
				)

		def set_rows(self, row0, row1, row2, row3):
			"""Set matrix from rows."""
			self.m_11, self.m_12, self.m_13, self.m_14 = row0
			self.m_21, self.m_22, self.m_23, self.m_24 = row1
			self.m_31, self.m_32, self.m_33, self.m_34 = row2
			self.m_41, self.m_42, self.m_43, self.m_44 = row3

	class Data(pyffi.object_models.FileFormat.Data):
		"""A class to contain the actual Ms2 data."""
		def __init__(self):
			self.version = 0
			self.mdl2_header = Ms2Format.Mdl2InfoHeader()
			self.ms2_header = Ms2Format.Ms2InfoHeader()
		
		def inspect_quick(self, stream):
			"""Quickly checks if stream contains DDS data, and gets the
			version, by looking at the first 8 bytes.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pos = stream.tell()
			try:
				magic, self.version, self.user_version = struct.unpack("<4s2I", stream.read(12))
				print("magic, self.version, self.user_version",magic, self.version, self.user_version)
			finally:
				stream.seek(pos)

		# overriding pyffi.object_models.FileFormat.Data methods

		def inspect(self, stream):
			"""Quickly checks if stream contains DDS data, and reads the
			header.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pos = stream.tell()
			try:
				self.inspect_quick(stream)
				self.mdl2_header.read(stream, data=self)
			finally:
				stream.seek(pos)
		
		def read(self, stream, verbose=0, file="", quick=False, map_bytes=False):
			"""Read a dds file.

			:param stream: The stream from which to read.
			:type stream: ``file``
			"""
			start_time = time.time()
			# store file name for later
			if file:
				self.file = file
				self.dir, self.basename = os.path.split(file)
				self.file_no_ext = os.path.splitext(self.file)[0]
			self.inspect_quick(stream)
			
			# read the file
			self.mdl2_header.read(stream, data=self)
			print(self.mdl2_header)
			
			# extra stuff
			self.bone_info = None
			base = self.mdl2_header.model_info.pack_offset
			# print("pack base",base)
		
			self.ms2_path = os.path.join(self.dir, self.mdl2_header.name.decode())
			with open(self.ms2_path, "rb") as ms2_stream:
				self.ms2_header.read(ms2_stream, data=self)
				# print(self.ms2_header)
				self.eoh = ms2_stream.tell()
				print("end of header: ",self.eoh)
				# first get all bytes of the whole bone infos block
				bone_info_bytes = ms2_stream.read(self.ms2_header.bone_info_size)
				# find the start of each using this identifier
				zero_f = bytes.fromhex("00 00 00 00")
				one_f = bytes.fromhex("00 00 80 3F")
				# lion has a 1 instead of a 4
				bone_info_marker_1 = bytes.fromhex("FF FF 00 00 00 00 00 00 01")
				# this alone is not picky enough for mod_f_wl_unq_laboratory_corner_002_dst
				bone_info_marker_4 = bytes.fromhex("FF FF 00 00 00 00 00 00 04")
				# there's 8 bytes before this
				bone_info_starts = []
				for a, b in ((zero_f, bone_info_marker_1),
							 (one_f, bone_info_marker_1),
							 (zero_f, bone_info_marker_4),
							 (one_f, bone_info_marker_4),
							 ):
					bone_info_starts.extend(x-4 for x in findall(a+b, bone_info_bytes))

				bone_info_starts = list(sorted(bone_info_starts))
				print("bone_info_starts",bone_info_starts)

				if bone_info_starts:
					idx = self.mdl2_header.index
					if idx >= len(bone_info_starts):
						print("reset boneinfo index")
						idx = 0
					bone_info_address = self.eoh + bone_info_starts[idx]
					print("using bone info {} at address {}".format(idx, bone_info_address) )
					ms2_stream.seek(bone_info_address)
					self.bone_info = Ms2Format.Ms2BoneInfo()
					self.bone_info.read(ms2_stream, data=self)
					print(self.bone_info)
					print("end of bone info at", ms2_stream.tell())
					
					self.bone_names = [self.ms2_header.names[i] for i in self.bone_info.name_indices]
				else:
					print("No bone info found")
					self.bone_names = []
				ms2_stream.seek(self.eoh + self.ms2_header.bone_info_size)
				# get the starting position of buffer #2, vertex & face array
				self.start_buffer2 = ms2_stream.tell()
				print("vert array start", self.start_buffer2 )
				print("tri array start", self.start_buffer2 + self.ms2_header.buffer_info.vertexdatasize)
				
				if not quick:
					for model in self.mdl2_header.models:
						model.populate(self, ms2_stream, self.start_buffer2, self.bone_names, base)

				if map_bytes:
					for model in self.mdl2_header.models:
						model.read_bytes_map(self.start_buffer2, ms2_stream)
					return

			# set material links
			for mat_1 in self.mdl2_header.materials_1:
				try:
					name = self.ms2_header.names[mat_1.material_index]
					model = self.mdl2_header.models[mat_1.model_index]
					model.material = name
				except:
					print(f"Couldn't match material {mat_1.material_index} to model {mat_1.model_index} - bug?")
			# todo - doesn't seem to be correct, at least not for JWE dinos
			self.mdl2_header.lod_names = [self.ms2_header.names[lod.strznameidx] for lod in self.mdl2_header.lods]
			print("lod_names", self.mdl2_header.lod_names)
			print(f"Finished reading in {time.time()-start_time:.2f} seconds!")

		def write(self, stream, verbose=0, file=""):
			"""Write a dds file.

			:param stream: The stream to which to write.
			:type stream: ``file``
			:param verbose: The level of verbosity.
			:type verbose: ``int``
			"""
				
			exp = "export"
			exp_dir = os.path.join(self.dir, exp)
			os.makedirs(exp_dir, exist_ok=True)
			print("Writing verts and tris to temporary buffer")
			# write each model's vert & tri block to a temporary buffer
			temp_vert_writer = io.BytesIO()
			temp_tris_writer = io.BytesIO()
			temp_bone_writer = io.BytesIO()
			vert_offset = 0
			tris_offset = 0

			new_bone_info = self.bone_info
			new_bone_info.write(temp_bone_writer, data=self)
           
			print("new bone info length: ",len(temp_bone_writer.getvalue()))
			for i, model in enumerate(self.mdl2_header.models):
				model.write_verts(temp_vert_writer, data=self)
				model.write_tris(temp_tris_writer, data=self)
				print("vert_offset",vert_offset)
				print("tris_offset",tris_offset)
				
				# update ModelData struct
				model.vertex_offset = vert_offset
				model.tri_offset = tris_offset
				model.vertex_count = len(model.verts)
				model.tri_index_count = len(model.tri_indices)
				
				# offsets for the next model
				vert_offset = temp_vert_writer.tell()
				tris_offset = temp_tris_writer.tell()
			
			# update lod fragment
			print("update lod fragment")
			for lod in self.mdl2_header.lods:
				# print(lod)
				lod_models = tuple(model for model in self.mdl2_header.models[lod.first_model_index:lod.last_model_index])
				# print(lod_models)
				lod.vertex_count = sum(model.vertex_count for model in lod_models)
				lod.tri_index_count = sum(model.tri_index_count for model in lod_models)
				print("lod.vertex_count",lod.vertex_count)
				print("lod.tri_index_count",lod.tri_index_count)
			print("Writing final output")
			# get original header and buffers 0 & 1
			input_ms2_name = self.mdl2_header.name.decode()
			self.ms2_path = os.path.join(self.dir, input_ms2_name)
			with open(self.ms2_path, "rb") as ms2_stream:
				self.ms2_header.read(ms2_stream, data=self)
				# print(self.ms2_header)
				self.eoh = ms2_stream.tell()      

                
				print("end of header: ",self.eoh)
				# first get all bytes of the whole bone infos block
				bone_info_bytes = ms2_stream.read(self.ms2_header.bone_info_size)
				print("old bone info length: ",len(bone_info_bytes))
				cut =len(temp_bone_writer.getvalue()) - len(bone_info_bytes)
                
                
                
                
			
			# get bytes from IO object
			vert_bytes = temp_vert_writer.getvalue()
			tris_bytes = temp_tris_writer.getvalue()
			bone_bytes = temp_bone_writer.getvalue()
			# modify buffer size
			self.ms2_header.buffer_info.vertexdatasize = len(vert_bytes)
			self.ms2_header.buffer_info.facesdatasize = len(tris_bytes)

			mdl2_name = os.path.basename(file)

			# create name of output ms2
			new_ms2_name = mdl2_name.rsplit(".",1)[0]+".ms2"
			ms2_path = os.path.join(exp_dir, new_ms2_name)
			
			# write output ms2
			with open(ms2_path, "wb") as f:
				self.ms2_header.write(f, data=self)
				f.write(bone_bytes)
				if cut != 0:
					f.write(bone_info_bytes[cut:])
				f.write(vert_bytes)
				f.write(tris_bytes)
				
			# set new ms2 name to mdl2 header
			self.mdl2_header.name = new_ms2_name.encode()
			
			# write final mdl2
			mdl2_path = os.path.join(exp_dir, mdl2_name)
			with open(mdl2_path, "wb") as f:
				self.mdl2_header.write(f, data=self)
	
	class ModelData:
		
		# def __init__(self, **kwargs):
			# BasicBase.__init__(self, **kwargs)
			# self.set_value(False)

		def read_bytes_map(self,  start_buffer2, stream):
			"""Used to document byte usage of different vertex formats"""
			# read a vertices of this model
			stream.seek(start_buffer2 + self.vertex_offset)
			# read the packed data
			data = np.fromfile(stream, dtype=np.ubyte, count=self.size_of_vertex * self.vertex_count)
			data = data.reshape((self.vertex_count, self.size_of_vertex ))
			self.bytes_map = np.max(data, axis=0)
			if self.size_of_vertex != 48:
				raise AttributeError(f"size_of_vertex != 48: size_of_vertex {self.size_of_vertex}, flag {self.flag}", )
			# print(self.size_of_vertex, self.flag, self.bytes_map)

		def init_arrays(self, count):
			self.vertex_count = count
			self.vertices = np.empty( (self.vertex_count, 3), np.float32 )
			self.normals = np.empty( (self.vertex_count, 3), np.float32 )
			self.tangents = np.empty( (self.vertex_count, 3), np.float32 )
			try:
				uv_shape = self.dt["uvs"].shape
				self.uvs = np.empty( (self.vertex_count, *uv_shape), np.float32 )
			except:
				self.uvs = None
			try:
				colors_shape = self.dt["colors"].shape
				self.colors = np.empty( (self.vertex_count, *colors_shape), np.float32 )
			except:
				self.colors = None
			self.weights = []

		def get_vcol_count(self,):
			if "colors" in self.dt.fields:
				return self.dt["colors"].shape[0]
			return 0

		def get_uv_count(self,):
			if "uvs" in self.dt.fields:
				return self.dt["uvs"].shape[0]
			return 0

		def update_dtype(self):
			"""Update ModelData.dt (numpy dtype) according to ModelData.flag"""
			# basic shared stuff
			dt = [
				("pos", np.uint64),
				("normal", np.ubyte, (3,)),
				("unk", np.ubyte),
				("tangent", np.ubyte, (3,)),
				("bone index", np.ubyte),
				]
			# uv variations
			if self.flag == 529:
				dt.extend([
					("uvs", np.ushort, (2, 2)),
					("zeros0", np.int32, (2,))
				])
			elif self.flag == 528:
				dt.extend([
					("uvs", np.ushort, (1, 2)),
					("zeros0", np.int32, (3,))
				])
			elif self.flag in (1013,821):
				dt.extend([
					("uvs", np.ushort, (3, 2)),
					("zeros0", np.int32, (1,))
				])
			elif self.flag in (885, 565):
				dt.extend([
					("uvs", np.ushort, (3, 2)),
					("zeros0", np.int32, (1,))
				])
			elif self.flag == 533:
				dt.extend([
					# see walls_gate.mdl2, two uv layers
					("uvs", np.ushort, (2, 2)),
					("colors", np.ubyte, (1, 4)),
					("zeros2", np.int32, (1,))
				])
			elif self.flag == 513:
				dt.extend([
					("uvs", np.ushort, (2, 2)),
					# ("colors", np.ubyte, (1, 4)),
					("zeros2", np.uint64, (3,))
				])
			elif self.flag == 512:
				dt.extend([
					# tree_birch_white_03 - apparently 8 uvs
					("uvs", np.ushort, (8, 2)),
				])
			elif self.flag == 517:
				dt.extend([
					# trees seem to have two uvs, then something like normals
					("uvs", np.ushort, (2, 2)),
					("colors", np.ubyte, (6, 4)),
				])

			# bone weights
			if self.flag in (529, 533, 885, 565, 1013, 528, 821):
				dt.extend([
					("bone ids", np.ubyte, (4,)),
					("bone weights", np.ubyte, (4,)),
					("zeros1", np.uint64)
				])
			self.dt = np.dtype(dt)
			if self.dt.itemsize != self.size_of_vertex:
				raise AttributeError(f"Vertex size for flag {self.flag} is wrong! Collected {self.dt.itemsize}, got {self.size_of_vertex}")

		def read_verts(self, stream, data):
			# read a vertices of this model
			stream.seek(self.start_buffer2 + self.vertex_offset)
			# get dtype according to which the vertices are packed
			self.update_dtype()
			# read the packed data
			self.verts_data = np.fromfile(stream, dtype=self.dt, count=self.vertex_count)
			# create arrays for the unpacked data
			self.init_arrays(self.vertex_count)
			# first cast to the float uvs array so unpacking doesn't use int division
			if self.uvs is not None:
				self.uvs[:] = self.verts_data[:]["uvs"]
				# unpack uvs
				self.uvs = (self.uvs - 32768) / 2048
			if self.colors is not None:
				# first cast to the float colors array so unpacking doesn't use int division
				self.colors[:] = self.verts_data[:]["colors"]
				self.colors /= 255
			self.normals[:] = self.verts_data[:]["normal"]
			self.tangents[:] = self.verts_data[:]["tangent"]
			self.normals = (self.normals - 128) / 128
			self.tangents = (self.tangents - 128) / 128
			for i in range(self.vertex_count):
				in_pos_packed = self.verts_data[i]["pos"]
				vert, residue = self.unpack_longint_vec(in_pos_packed)
				self.vertices[i] = self.unpack_swizzle(vert)

				out_pos_packed = self.pack_longint_vec(self.pack_swizzle(self.vertices[i]), residue)
				# print(bin(in_pos_packed), type(in_pos_packed))
				# print(bin(out_pos_packed), type(out_pos_packed))
				# print(in_pos_packed-out_pos_packed)

				self.normals[i] = self.unpack_swizzle(self.normals[i])
				self.tangents[i] = self.unpack_swizzle(self.tangents[i])

				# stores all (bonename, weight) pairs of this vertex
				vert_w = []
				if self.bone_names:
					if "bone ids" in self.dt.fields and residue:
						weights = self.get_weights(self.verts_data[i]["bone ids"], self.verts_data[i]["bone weights"])
						vert_w = [(self.bone_names[bone_i], w) for bone_i, w in weights]
					# fallback: skin parition
					if not vert_w:
						try:
							vert_w = [(self.bone_names[self.verts_data[i]["bone index"]], 1), ]
						except IndexError:
							# aviary landscape
							vert_w = [(str(self.verts_data[i]["bone index"]), 1), ]

				# create fur length vgroup
				if self.flag in (1013,821,885):
					vert_w.append(("fur_length", self.uvs[i][1][0]))

				# the unknown 0, 128 byte
				vert_w.append(("unk0", self.verts_data[i]["unk"]/255))
				# packing bit
				vert_w.append(("residue", residue))
				self.weights.append(vert_w)

		@staticmethod
		def unpack_ushort_vector(vec):
			return (vec - 32768) / 2048

		@staticmethod
		def unpack_swizzle(vec):
			# swizzle to avoid a matrix multiplication for global axis correction
			return -vec[0], -vec[2], vec[1]

		@staticmethod
		def pack_swizzle(vec):
			# swizzle to avoid a matrix multiplication for global axis correction
			return -vec[0], vec[2], -vec[1]

		@staticmethod
		def pack_ushort_vector(vec):
			return [min(int(round(coord * 2048 + 32768)), 65535) for coord in vec]

		@staticmethod
		def pack_ubyte_vector(vec):
			return [min(int(round(x * 128 + 128)), 255) for x in vec]

		@staticmethod
		def get_weights(bone_ids, bone_weights):
			return [(i, w / 255) for i, w in zip(bone_ids, bone_weights) if w > 0]

		def unpack_longint_vec(self, input):
			"""Unpacks and returns the self.raw_pos uint64"""
			# numpy uint64 does not like the bit operations so we cast to default int
			input = int(input)
			# correct for size according to base, relative to 512
			scale = self.base / 512 / 2048
			# input = self.raw_pos
			output = []
			# print("inp",bin(input))
			for i in range(3):
				# print("\nnew coord")
				# grab the last 20 bits with bitand
				# bit representation: 0b11111111111111111111
				twenty_bits = input & 0xFFFFF
				# print("input", bin(input))
				# print("twenty_bits = input & 0xFFFFF ", bin(twenty_bits), twenty_bits)
				input >>= 20
				# print("input >>= 20", bin(input))
				# print("1",bin(1))
				# get the rightmost bit
				rightmost_bit = input & 1
				# print("rightmost_bit = input & 1",bin(rightmost_bit))
				# print(rightmost_bit, twenty_bits)
				if not rightmost_bit:
					# rightmost bit was 0
					# print("rightmost_bit == 0")
					# bit representation: 0b100000000000000000000
					twenty_bits -= 0x100000
				# print("final int", twenty_bits)
				o = (twenty_bits + self.base) * scale
				output.append(o)
				# shift to skip the sign bit
				input >>= 1
			# input at this point is either 0 or 1
			return output, input

		def pack_longint_vec(self, vec, residue):
			"""Packs the input vector + residue bit into a uint64 (1, 21, 21, 21)"""
			# correct for size according to base, relative to 512
			scale = self.base / 512 / 2048
			output = 0
			for i, f in enumerate(vec):
				o = int(round(f / scale - self.base))
				# print("restored int", o)
				if o < 0x100000:
					# 0b100000000000000000000
					o += 0x100000
				else:
					# set the 1 bit flag
					output |= 1 << (21*(i+1)-1)
				# print("restored int + correction", o)
				output |= o << (21*i)
			# print("bef",bin(output))
			output |= residue << 63
			# thing = struct.unpack("<d", struct.pack("<Q",output))
			# thing2 = -1.0*float(thing[0])
			# output = struct.unpack("<Q", struct.pack("<d",thing2))[0]
			return output

		def write_verts(self, stream, data):
			# if writing directly to file, doesn't support io bytes
			# self.verts_data.tofile(stream)
			stream.write(self.verts_data.tobytes())
			
		def read_tris(self, stream, data):
			# read all tri indices for this model
			stream.seek( self.start_buffer2 + data.ms2_header.buffer_info.vertexdatasize + self.tri_offset )
			# print("tris offset",stream.tell())
			# read all tri indices for this model segment
			self.tri_indices = list( struct.unpack( str(self.tri_index_count)+"H", stream.read( self.tri_index_count*2 ) ) )
		
		def write_tris(self, stream, data):
			stream.write( struct.pack( str(len(self.tri_indices))+"H", *self.tri_indices ) )
		
		@property
		def lod_index(self,):
			try:
				lod_i = int(math.log2(self.poweroftwo))
			except:
				lod_i = 0
				print("EXCEPTION: math domain for lod",self.poweroftwo)
			return lod_i
			
		@lod_index.setter
		def lod_index(self, lod_i):
			self.poweroftwo = int(math.pow(2, lod_i))

		def set_verts(self, verts):
			"""Update self.verts_data from list of new verts"""
			self.verts = verts
			self.verts_data = np.zeros(len(verts), dtype=self.dt)
			for i, (position, residue, normal, unk_0, tangent, bone_index, uvs, vcols, bone_ids, bone_weights, fur) in enumerate(verts):
				self.verts_data[i]["pos"] = self.pack_longint_vec(self.pack_swizzle(position), residue)
				self.verts_data[i]["normal"] = self.pack_ubyte_vector(self.pack_swizzle(normal))
				self.verts_data[i]["tangent"] = self.pack_ubyte_vector(self.pack_swizzle(tangent))
				self.verts_data[i]["unk"] = unk_0*255
				self.verts_data[i]["bone index"] = bone_index
				if "bone ids" in self.dt.fields:
					self.verts_data[i]["bone ids"] = bone_ids
					# round is essential so the float is not truncated
					self.verts_data[i]["bone weights"] = list(round(w*255) for w in bone_weights)
					# additional double check
					d = np.sum(self.verts_data[i]["bone weights"]) - 255
					self.verts_data[i]["bone weights"][0] -= d
				if "uvs" in self.dt.fields:
					self.verts_data[i]["uvs"] = list(self.pack_ushort_vector(uv) for uv in uvs)
					if fur is not None:
						self.verts_data[i]["uvs"][1][0], _ = self.pack_ushort_vector((fur, 0))
				if "colors" in self.dt.fields:
					self.verts_data[i]["colors"] = list(list(c*255 for c in vcol) for vcol in vcols)

		@property
		def tris(self,):
			# create non-overlapping tris
			# reverse to account for the flipped normals from mirroring in blender
			return [(self.tri_indices[i+2], self.tri_indices[i+1], self.tri_indices[i]) for i in range(0, len(self.tri_indices), 3)]
			
		@tris.setter
		def tris(self, b_tris):
			# clear tri array
			self.tri_indices = []
			for tri in b_tris:
				# reverse to account for the flipped normals from mirroring in blender
				self.tri_indices.extend( reversed(tri) )
			
			
		def populate(self, data, ms2_stream, start_buffer2, bone_names = [], base = 512):
			self.start_buffer2 = start_buffer2
			self.data = data
			self.base = base
			self.bone_names = bone_names
			self.read_verts(ms2_stream, self.data)
			self.read_tris(ms2_stream, self.data)
			
	class JweBone:

		def set_bone(self, matrix):
			pos,quat,sca = matrix.decompose()
			self.loc.x,self.loc.y,self.loc.z = -1*pos.y,pos.z,pos.x
			self.rot.x, self.rot.y, self.rot.z, self.rot.w = quat.y, -1*quat.z, -1*quat.x, quat.w
			self.scale = sca.x

            
            
            
            
            
            
            
            
