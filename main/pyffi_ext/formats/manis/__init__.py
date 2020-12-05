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


class ManisFormat(pyffi.object_models.xml.FileFormat):
	"""This class implements the Manis format."""
	xml_file_name = 'manis.xml'
	# where to look for manis.xml and in what order:
	# MANISXMLPATH env var, or ManisFormat module directory
	xml_file_path = [os.getenv('MANISXMLPATH'), os.path.dirname(__file__)]
	# file name regular expression match
	RE_FILENAME = re.compile(r'^.*\.manis$', re.IGNORECASE)
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

	class Data(pyffi.object_models.FileFormat.Data):
		"""A class to contain the actual Manis data."""
		def __init__(self):
			self.version = 0
			self.header = ManisFormat.InfoHeader()
			# self.manis_header = ManisFormat.ManisInfoHeader()
		
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

		def read_z_str(self, stream):
			"""get a zero terminated string from stream at pos """
			# stream.seek( pos )
			z_str = ManisFormat.ZString()
			z_str.read(stream, data=self)
			return str(z_str)

		def read(self, stream, verbose=0, file="", quick=False):
			"""Read a dds file.

			:param stream: The stream from which to read.
			:type stream: ``file``
			"""
			# store file name for later
			if file:
				self.file = file
				self.dir, self.basename = os.path.split(file)
				self.file_no_ext = os.path.splitext(self.file)[0]
			self.inspect_quick(stream)

			# read the file
			self.header.read(stream, data=self)
			print(self.header)
			name_count = self.header.header.hash_block_size // 4
			hashes = struct.unpack(f"<{name_count}I", stream.read(name_count*4))
			names = [ self.read_z_str(stream) for _ in range(name_count) ]
			print(name_count)
			print(hashes, names)

			# read the first mani data
			mani_info = self.header.mani_infos[0]
			name_indices_0 = struct.unpack(f"<{mani_info.c}I", stream.read(mani_info.c * 4))
			print("name_indices_0", name_indices_0)
			name_indices_1 = struct.unpack(f"<{mani_info.name_count}I", stream.read(mani_info.name_count * 4))
			print("name_indices_1", name_indices_1)
			name_indices_2 = struct.unpack(f"<{mani_info.e}I", stream.read(mani_info.e * 4))
			print("name_indices_2", name_indices_2)
			p_indices_0 = struct.unpack(f"<{mani_info.c}B", stream.read(mani_info.c))
			print("p_indices_0", p_indices_0)
			p_indices_1 = struct.unpack(f"<{mani_info.name_count}B", stream.read(mani_info.name_count))
			print("p_indices_1", p_indices_1)
			p_indices_2 = struct.unpack(f"<{mani_info.e}B", stream.read(mani_info.e))
			print("p_indices_2", p_indices_2)

			# seems to be pretty good until here, then it breaks

			# flags per frame?
			frames_0 = [ struct.unpack(f"<4B", stream.read(4)) for i in range(mani_info.frame_count)]
			print("frames_0", frames_0)
			print("pad", stream.read(1))
			# could be bitfields per frame?
			frames_1 = struct.unpack(f"<{mani_info.frame_count}I", stream.read(mani_info.frame_count * 4))
			print("frames_1", frames_1)
			zerom, frame_count, name_count, c_count = struct.unpack(f"<4I", stream.read(4 * 4))
			print("zerom, frame_count, name_count, c_count",zerom, frame_count, name_count, c_count)
			print("zeros", stream.read(76))
			x, y = struct.unpack(f"<2H", stream.read(4))
			print("x, y", x, y)

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
			# write each model's vert & tri block to a temporary buffer
			temp_vert_writer = io.BytesIO()
			temp_tris_writer = io.BytesIO()
			vert_offset = 0
			tris_offset = 0
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
				print(lod)
				lod_models = tuple(model for model in self.mdl2_header.models[lod.first_model_index:lod.last_model_index])
				print(lod_models)
				lod.vertex_count = sum(model.vertex_count for model in lod_models)
				lod.tri_index_count = sum(model.tri_index_count for model in lod_models)
				print("lod.vertex_count",lod.vertex_count)
				print("lod.tri_index_count",lod.tri_index_count)
				
			# get original header and buffers 0 & 1
			input_manis_name = self.mdl2_header.name.decode()
			self.manis_path = os.path.join(self.dir, input_manis_name)
			with open(self.manis_path, "rb") as manis_stream:
				self.manis_header.read(manis_stream, data=self)
				buffer_1 = manis_stream.read(self.manis_header.bone_info_size)
			
			# get bytes from IO object
			vert_bytes = temp_vert_writer.getvalue()
			tris_bytes = temp_tris_writer.getvalue()
			
			# modify buffer size
			self.manis_header.buffer_info.vertexdatasize = len(vert_bytes)
			self.manis_header.buffer_info.facesdatasize = len(tris_bytes)
			
			# create name of output manis
			# temp_manis_name = input_manis_name.rsplit(".",1)[0]+"_export.manis"
			manis_path = os.path.join(exp_dir, input_manis_name)
			
			# write output manis
			with open(manis_path, "wb") as f:
				self.manis_header.write(f, data=self)
				f.write(buffer_1)
				f.write(vert_bytes)
				f.write(tris_bytes)
				
			# set new manis name to mdl2 header
			# self.mdl2_header.name = temp_manis_name.encode()
			
			# write final mdl2
			dir, mdl2_name = os.path.split(file)
			mdl2_path = os.path.join(exp_dir, mdl2_name)
			with open(mdl2_path, "wb") as f:
				self.mdl2_header.write(f, data=self)
	
	class ModelData:
		
        # def __init__(self, **kwargs):
            # BasicBase.__init__(self, **kwargs)
            # self.set_value(False)
			
		def read_verts(self, stream, data):
			# read a vertices of this model
			stream.seek( self.start_buffer2 + self.vertex_offset )
			# print("verts offset",stream.tell())
			for i in range(self.vertex_count):
				vert = ManisFormat.PackedVert()
				vert.read(stream, data=data)
				vert.base = self.base
				self.verts.append(vert)
				self.vertices.append( vert.position )
				self.normals.append( vert.normal  )
				self.tangents.append( vert.tangent	)
				for col_i in range(2):
					self.colors[col_i].append( vert.colors[col_i] )
				if self.bone_names:
					# all (bonename, weight) pairs of this vertex
					if self.flag == 517 or self.flag == 512:
						vert_w = [ (str(bone_i), w) for bone_i, w in vert.weights ]
					else:
						vert_w = [ (self.bone_names[bone_i], w) for bone_i, w in vert.weights ]
					# fallback: skin parition
					if not vert_w:
						try:
							# aviary landscape, probably a differnt vert struct
							vert_w = [ (self.bone_names[vert.bone_index], 1), ]
						except:
							pass
				else:
					vert_w = []
				for i, (uv_coord, layer) in enumerate(zip(vert.uvs, self.uv_layers)):
					# create fur length vgroup
					if i == 1 and self.flag == 885:
						vert_w.append( ("fur_length", uv_coord[0] ) )
						
					layer.append(uv_coord)
				# the unknown 0, 128 byte
				vert_w.append( ("unk0", vert.unk_0/255 ) )
				self.weights.append(vert_w)
		
		def write_verts(self, stream, data):
			for vert in self.verts:
				vert.write(stream, data)
			
		def read_tris(self, stream, data):
			# read all tri indices for this model
			stream.seek( self.start_buffer2 + data.manis_header.buffer_info.vertexdatasize + self.tri_offset )
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
			
			
		def populate(self, data, manis_stream, start_buffer2, bone_names = [], base = 512):
			self.start_buffer2 = start_buffer2
			self.data = data
			self.base = base
			self.bone_names = bone_names
			
			# create data lists for this model
			self.verts = []
			self.vertices = []
			self.normals = []
			self.tangents = []
			self.uv_layers = ( [], [], [], [] )
			self.colors = ( [], [] )
			self.weights = []
			self.read_verts(manis_stream, self.data)
			self.read_tris(manis_stream, self.data)
			
		
			
	class PackedVert:
		base = 512
        # def __init__(self, **kwargs):
            # BasicBase.__init__(self, **kwargs)
            # self.set_value(False)
		
		
		def unpack_ushort_vector(self, vec):
			return [ (coord - 32768) / 2048 for coord in (vec.u, vec.v) ]
			
		def pack_ushort_vector(self, vec):
			return [ min(int(round(coord * 2048 + 32768)), 65535) for coord in vec]
			
		def unpack_ubyte_vector(self, vec):
			vec = (vec.x, vec.y, vec.z)
			vec = [(x-128)/128 for x in vec]
			# swizzle to avoid a matrix multiplication for global axis correction
			return -vec[0], -vec[2], vec[1]
			
		def pack_ubyte_vector(self, vec):
			# swizzle to avoid a matrix multiplication for global axis correction
			vec = (-vec[0], vec[2], -vec[1])
			return [min(int(round(x*128+128)), 255) for x in vec]
		
		@property
		def position(self):
			"""Unpacks and returns the self.raw_pos uint64"""
			# print("\nunpacking")
			# correct for size according to base, relative to 512
			scale = self.base / 512 / 2048
			input = self.raw_pos
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
				# when doing this, the output mesh is fine for coords that don't exceed approximately 0.25
				# if True:
					# rightmost bit was 0
					# print("rightmost_bit == 0")
					# bit representation: 0b100000000000000000000
					twenty_bits -= 0x100000
				# print("final int", twenty_bits)
				o = (twenty_bits + self.base) * scale
				output.append(o)
				# shift to skip the sign bit
				input >>= 1
			# the inidividual coordinates
			x,y,z = output
			# swizzle to avoid a matrix multiplication for global axis correction
			return [-x,-z,y]

		@position.setter
		def position(self, vec):
			"""Packs the input into the self.raw_pos uint64"""
			# print("\npacking")
			# swizzle to avoid a matrix multiplication for global axis correction
			x,y,z = vec
			input = (-x,z,-y)
			# correct for size according to base, relative to 512
			scale = self.base / 512 / 2048
			output = 0
			for i, f in enumerate(input):
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
				# print(bin(output))
				# print(bin(o))
			# output |= 1 << 63
			# print(bin(output))
			#print(str(struct.unpack("Q",struct.pack("d",struct.unpack("d",struct.pack("Q",output))))))
			thing=struct.unpack("<d",struct.pack("<Q",output))
			thing2 = -1.0*float(thing[0])
			thing3 = struct.unpack("<Q",struct.pack("<d",thing2))
			output= thing3[0]
			# print("out",bin(output))
			# return output
			self.raw_pos = output	

		@property
		def normal(self,):
			return self.unpack_ubyte_vector(self.raw_normal)
			
		@normal.setter
		def normal(self, value):
			self.raw_normal.x, self.raw_normal.y, self.raw_normal.z = self.pack_ubyte_vector(value)
		
		@property
		def tangent(self,):
			return self.unpack_ubyte_vector(self.raw_tangent)
			
		@tangent.setter
		def tangent(self, value):
			self.raw_tangent.x, self.raw_tangent.y, self.raw_tangent.z = self.pack_ubyte_vector(value)
		
		@property
		def uvs(self,):
			return [self.unpack_ushort_vector(uv) for uv in self.raw_uvs]
		
		@uvs.setter
		def uvs(self, uv_layers):
			for uv, uv_coord in zip(self.raw_uvs, uv_layers):
				uv.u, uv.v = self.pack_ushort_vector(uv_coord)
		
		@property
		def fur_length(self,):
			return self.unpack_ushort_vector(self.raw_uvs[1])[0]
			
		@fur_length.setter
		def fur_length(self, f):
			self.raw_uvs[1].u, _ = self.pack_ushort_vector( (f, 0) )
		
		@property
		def weights(self,):
			out = []
			for i, w in zip(self.bone_ids, self.bone_weights):
				if w > 0:
					out.append( (i, w/255) )
			return out
		
		@weights.setter
		def weights(self, weights):
			assert( len(weights) == 4 )
			# assume len(w) == 4, each is a tuple of (bone index, weight) or (0, 0)
			for i, (new_i, new_w) in enumerate(weights):
				self.bone_ids[i] = new_i
				self.bone_weights[i] = min(int(round(new_w * 255)), 255)
				
		
		# # @property
		# def position(self, base):
			# """ Set this vector to values from another object that supports iteration or x,y,z properties """
			# return read_packed_vector(self.raw_pos, base)
				
		# def __iter__(self):
			# # just a convenience so we can do: x,y,z = Vector3()
			# yield self.x
			# yield self.y
			# yield self.z
            