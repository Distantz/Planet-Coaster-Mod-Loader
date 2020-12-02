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

class FgmFormat(pyffi.object_models.xml.FileFormat):
	"""This class implements the Fgm format."""
	xml_file_name = 'fgm.xml'
	# where to look for fgm.xml and in what order:
	# FGMXMLPATH env var, or FgmFormat module directory
	xml_file_path = [os.getenv('FGMXMLPATH'), os.path.dirname(__file__)]
	# file name regular expression match
	RE_FILENAME = re.compile(r'^.*\.fgm$', re.IGNORECASE)
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
		# maps FGM dtype to struct dtype
		# dtypes = {0:"f", 1:"ff", 2:"fff", 3:"ffff", 4:"I", 5:"i", 6:"i", 8:"I"}
		dtypes = {0:"f", 1:"ff", 2:"fff", 3:"ffff", 5:"i", 6:"i"}

		"""A class to contain the actual Fgm data."""
		def __init__(self):
			self.version = 0
			self.fgm_header = FgmFormat.FgmInfoHeader()
		
		@property
		def game(self,):
			# JWE style
			if self.fgm_header.flag_2 == 24724:
				return "Jurassic World Evolution"
			# PC style
			elif self.fgm_header.version == 18:
				return "Jurassic World Evolution"
			# PZ Style
			elif self.fgm_header.flag_2 == 8340:
				return "Planet Zoo"
			else:
				return "Unknown Game"
		
		def inspect_quick(self, stream):
			"""Quickly checks if stream contains DDS data, and gets the
			version, by looking at the first 8 bytes.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pass

		def inspect(self, stream):
			"""Quickly checks if stream contains DDS data, and reads the
			header.

			:param stream: The stream to inspect.
			:type stream: file
			"""
			pass
		
		def write_z_str(self, stream, s):
			"""get a zero terminated string from stream at pos """
			z_str = FgmFormat.ZString()
			z_str.set_value(s.encode())
			z_str.write(stream, data=self)
			
		def read_z_str(self, stream, pos):
			"""get a zero terminated string from stream at pos """
			stream.seek( pos )
			z_str = FgmFormat.ZString()
			z_str.read(stream, data=self)
			return str(z_str)

		def read(self, stream, verbose=0, file="", quick=False):
			"""Read a fgm file.

			:param stream: The stream from which to read.
			:type stream: ``file``
			"""
			# store file name for later
			if file:
				self.file = file
				self.dir, self.basename = os.path.split(file)
				self.file_no_ext = os.path.splitext(self.file)[0]
			# self.inspect_quick(stream)
			
			# read the file
			self.fgm_header.read(stream, data=self)
			self.eoh = stream.tell()
			# print(self.fgm_header)
					
			zeros = stream.read(self.fgm_header.zeros_size)
			
			data_start = stream.tell()
			name_start = data_start + self.fgm_header.data_lib_size
			self.shader_name = self.read_z_str(stream, name_start)
			for texture in self.fgm_header.textures:
				texture.name = self.read_z_str(stream, name_start+texture.offset)
				# convert to bool
				texture.textured = texture.is_textured == 8
				if texture.textured:
					texture.value = list( x for x in texture.indices)
				else:
					texture.value = list( x for x in texture.colors)

			# read float / bool / int values
			for attrib in self.fgm_header.attributes:
				attrib.name = self.read_z_str(stream, name_start+attrib.offset)
				fmt = self.dtypes[attrib.dtype]
				stream.seek(data_start + attrib.first_value_offset)
				attrib.value = list(struct.unpack("<"+fmt, stream.read(struct.calcsize(fmt)) ))
				if attrib.dtype == 6:
					attrib.value = list( bool(v) for v in attrib.value )
			# self.print_readable()

		def print_readable(self,):
			print("\nShader =", self.shader_name)
			print("\nTextures")
			for texture in self.fgm_header.textures:
				l = "(textured)" if texture.textured else ""
				s = '{} {} = {}'.format(texture.name, l, texture.value)
				print(s)
				print(texture)
				print()
			print("\nAttributes")
			for attrib in self.fgm_header.attributes:
				s = '{} = {}'.format(attrib.name, attrib.value)
				print(s)
				print(attrib)
				print()
			
		def write(self, stream, verbose=0):
			"""Write a fgm file.

			:param stream: The stream to which to write.
			:param verbose: The level of verbosity.
			:type verbose: ``int``
			"""
			
			names_writer = io.BytesIO()
			data_writer = io.BytesIO()
			# shader name is at 0
			self.write_z_str(names_writer, self.shader_name)
			# attribs are written first
			for attrib in self.fgm_header.attributes:
				attrib.offset = names_writer.tell()
				self.write_z_str(names_writer, attrib.name)
				attrib.first_value_offset = data_writer.tell()
				fmt = self.dtypes[attrib.dtype]
				b = struct.pack("<"+fmt, *attrib.value )
				data_writer.write(b)
			for texture in self.fgm_header.textures:
				if texture.textured:
					for i in range(len(texture.indices)):
						# uint - hashes
						texture.indices[i] = max(0, texture.value[i])
				texture.offset = names_writer.tell()
				self.write_z_str(names_writer, texture.name)

			# write the output stream
			self.fgm_header.write(stream, data=self)
			stream.write(b"\x00"*self.fgm_header.zeros_size)
			stream.write(data_writer.getvalue())
			stream.write(names_writer.getvalue())