import struct
import os
import traceback

from modules.formats.DDS import write_dds
from modules.formats.MS2 import write_ms2

from generated.formats.bnk import BnkFile
from modules.util import write_sized_str

from util import texconv


def extract(archive, extract_fdb, extract_lua, extract_anim, extract_model, extract_tex, extract_shader, extract_text, extract_aux, extract_fct, extract_misc, show_dds, only_types=[], progress_callback=None):
	"""Extract the files, after all archives have been read"""
	# the actual export, per file type
	error_files = []
	skip_files = []
	# data types that we export starting from other file types but are not caught as deliberate cases
	exported_types = ["mani", "mdl2", "texturestream"]
	print("\nExtracting from archive", archive.archive_index)
	ss_max = len(archive.sized_str_entries)
	for ss_index, sized_str_entry in enumerate(archive.sized_str_entries):
		try:
			# for batch operations, only export those we need
			if only_types and sized_str_entry.ext not in only_types:
				continue
			# ignore types in the count that we export from inside other type exporters
			if sized_str_entry.ext in exported_types:
				continue
			elif sized_str_entry.ext == "banis" and extract_anim == True:
				write_banis(archive, sized_str_entry)
			elif sized_str_entry.ext == "bani" and extract_anim == True:
				write_bani(archive, sized_str_entry)
			elif sized_str_entry.ext == "manis" and extract_anim == True:
				write_manis(archive, sized_str_entry)
			elif sized_str_entry.ext == "fgm" and extract_shader == True:
				write_fgm(archive, sized_str_entry)
			elif sized_str_entry.ext == "ms2" and extract_model == True:
				write_ms2(archive, sized_str_entry)
			elif sized_str_entry.ext == "materialcollection" and extract_shader == True:
				write_materialcollection(archive, sized_str_entry)
			elif sized_str_entry.ext == "tex" and extract_tex == True:
				write_dds(archive, sized_str_entry, show_dds)
			elif sized_str_entry.ext == "lua" and extract_lua == True:
				write_lua(archive, sized_str_entry)
			elif sized_str_entry.ext == "assetpkg" and extract_misc == True:
				write_assetpkg(archive, sized_str_entry)
			elif sized_str_entry.ext == "fdb" and extract_fdb == True:
				write_fdb(archive, sized_str_entry)
			elif sized_str_entry.ext == "xmlconfig" and extract_misc == True:
				write_xmlconfig(archive, sized_str_entry)
			elif sized_str_entry.ext == "userinterfaceicondata" and extract_misc == True:
				write_userinterfaceicondata(archive, sized_str_entry)
			elif sized_str_entry.ext == "txt" and extract_text == True:
				write_txt(archive, sized_str_entry)
			elif sized_str_entry.ext == "bnk" and extract_aux == True:
				write_bnk(archive, sized_str_entry, show_dds, progress_callback)
			elif sized_str_entry.ext == "prefab" and extract_misc == True:
				write_prefab(archive, sized_str_entry)
			elif sized_str_entry.ext == "voxelskirt" and extract_misc == True:
				write_voxelskirt(archive, sized_str_entry)
			elif sized_str_entry.ext == "gfx" and extract_misc == True:
				write_gfx(archive, sized_str_entry)
			elif sized_str_entry.ext == "fct" and extract_fct == True:
				write_fct(archive, sized_str_entry)
			elif sized_str_entry.ext == "scaleformlanguagedata" and extract_misc == True:
				write_scaleform(archive, sized_str_entry)
			else:
				print("\nSkipping",sized_str_entry.name)
				skip_files.append(sized_str_entry.name)
				continue

			if progress_callback:
				progress_callback("Extracting " + sized_str_entry.name, value=ss_index, vmax=ss_max)
		except BaseException as error:
			print(f"\nAn exception occurred while extracting {sized_str_entry.name}")
			print(error)
			traceback.print_exc()
			error_files.append(sized_str_entry.name)
			
	return error_files, skip_files


def write_bnk(archive, sized_str_entry, show_dds, progress_callback):
	bnk = os.path.splitext(sized_str_entry.name)[0]
	bnk_path = f"{archive.ovl.file_no_ext}_{bnk}_bnk_b.aux"
	if os.path.isfile(bnk_path):
		if "_media_" not in bnk_path:
			print("skipping events bnk", bnk_path)
			return
		print("exporting", bnk_path)

		data = BnkFile()
		data.load(bnk_path)

		# if we want to see the dds, write it to the output dir
		tmp_dir = texconv.make_tmp(archive.dir, show_dds)
		wem_files = data.extract_audio(tmp_dir, bnk)
		texconv.wem_handle(wem_files, archive.dir, show_dds, progress_callback)
	else:
		raise FileNotFoundError(f"BNK / AUX archive expected at {bnk_path}!")
		
def write_voxelskirt(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	buffers = sized_str_entry.data_entry.buffer_datas

	#try:
	#	buffer_data = sized_str_entry.data_entry.buffer_datas[0]
	#	print("buffer size",len(buffer_data))
	#except:
	#	print("Found no buffer data for",name)
	#	buffer_data = b""
	#if len(sized_str_entry.fragments) != 2:
	#	print("must have 2 fragments")
	#	return
	# write voxelskirt
	with open(archive.indir(name), 'wb') as outfile:
		# write the sized str and buffers
		print(sized_str_entry.pointers[0].data)
		outfile.write( sized_str_entry.pointers[0].data )
		for buff in buffers:
			outfile.write(buff)
            
def write_gfx(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	buffers = sized_str_entry.data_entry.buffer_datas

	#try:
	#	buffer_data = sized_str_entry.data_entry.buffer_datas[0]
	#	print("buffer size",len(buffer_data))
	#except:
	#	print("Found no buffer data for",name)
	#	buffer_data = b""
	#if len(sized_str_entry.fragments) != 2:
	#	print("must have 2 fragments")
	#	return
	# write voxelskirt
	with open(archive.indir(name), 'wb') as outfile:
		# write the sized str and buffers
		print(sized_str_entry.pointers[0].data)
		outfile.write( sized_str_entry.pointers[0].data )
		for buff in buffers:
			outfile.write(buff)
			
def write_fct(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	buffers = sized_str_entry.data_entry.buffer_datas
	ss_len = len(sized_str_entry.pointers[0].data)/4
	ss_data = struct.unpack("<4f{}I".format(int(ss_len - 4)),sized_str_entry.pointers[0].data)
	pad_size = ss_data[8]
    
	data_sizes = (ss_data[10],ss_data[12],ss_data[14],ss_data[16])
	adder = 0
	for x, data_size in enumerate(data_sizes):
		if data_size != 0:
			type_check = struct.unpack("<4s", buffers[0][pad_size+adder:pad_size+adder+4])[0]
			print(type_check)
			if "OTTO" in str(type_check):
				with open(archive.indir(name)+str(x)+".otf", 'wb') as outfile:
					for buff in buffers:
						outfile.write(buff[pad_size+adder:data_size+pad_size+adder])
			else:
				with open(archive.indir(name)+str(x)+".ttf", 'wb') as outfile:
					for buff in buffers:
						outfile.write(buff[pad_size+adder:data_size+pad_size+adder])
		adder += data_size
    
	#with open(archive.indir(name)+".pad", 'wb') as outfile:
		#for buff in buffers:
			#outfile.write(buff[0:pad_size])
       
	#with open(archive.indir(name)+".meta", 'wb') as outfile:
		#print(sized_str_entry.pointers[0].data)
		#outfile.write( sized_str_entry.pointers[0].data )
            
def write_scaleform(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
    
       
	with open(archive.indir(name), 'wb') as outfile:
		# write each of the fragments
		#print(sized_str_entry.pointers[0].data)
		outfile.write( sized_str_entry.pointers[0].data )
		for frag in sized_str_entry.fragments:
			#print(frag.pointers[0].data)
			#print(frag.pointers[1].data)
			outfile.write( frag.pointers[0].data )
			outfile.write( frag.pointers[1].data )
		
def write_prefab(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	
	try:
		buffer_data = sized_str_entry.data_entry.buffer_datas[0]
		print("buffer size",len(buffer_data))
	except:
		print("Found no buffer data for",name)
		buffer_data = b""
	#if len(sized_str_entry.fragments) != 2:
	#	print("must have 2 fragments")
	#	return
	# write lua
	#with open(archive.indir(name), 'wb') as outfile:
	#	# write the buffer
	#	outfile.write(buffer_data)

	with open(archive.indir(name), 'wb') as outfile:
		# write each of the fragments
		#print(sized_str_entry.pointers[0].data)
		outfile.write( sized_str_entry.pointers[0].data )
		for frag in sized_str_entry.fragments:
			#print(frag.pointers[0].data)
			#print(frag.pointers[1].data)
			outfile.write( frag.pointers[0].data )
			outfile.write( frag.pointers[1].data )

def write_txt(archive, txt_sized_str_entry):
	# a bare sized str
	b = txt_sized_str_entry.pointers[0].data
	size = struct.unpack("<I", b[:4])[0]
	with open(archive.indir(txt_sized_str_entry.name), "wb") as f:
		f.write(b[4:4+size])


def write_banis(archive, sized_str_entry):
	name = sized_str_entry.name
	if not sized_str_entry.data_entry:
		print("No data entry for ",name)
		return
	buffers = sized_str_entry.data_entry.buffer_datas
	if len(buffers) != 1:
		print("Wrong amount of buffers for",name)
		return
	print("\nWriting",name)
	with open(archive.indir(name), 'wb') as outfile:
		outfile.write(buffers[0])


def write_bani(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	if len(sized_str_entry.fragments) != 1:
		print("must have 1 fragment")
		return
	for other_sized_str_entry in archive.sized_str_entries:
		if other_sized_str_entry.ext == "banis":
			banis_name = other_sized_str_entry.name
			break
	else:
		print("Found no banis file for bani animation!")
		return

	f = sized_str_entry.fragments[0]

	# write banis file
	with open(archive.indir(name), 'wb') as outfile:
		outfile.write(b"BANI")
		write_sized_str(outfile, banis_name)
		outfile.write( f.pointers[0].data )
		outfile.write( f.pointers[1].data )


def write_manis(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting", name)
	if not sized_str_entry.data_entry:
		print("No data entry for ", name)
		return
	ss_data = sized_str_entry.pointers[0].data
	print(len(ss_data),ss_data)
	buffers = sized_str_entry.data_entry.buffer_datas
	print(len(buffers))
	# if len(buffers) != 3:
	# 	print("Wrong amount of buffers for", name)
	# 	return
	names = [c.name for c in sized_str_entry.children]
	manis_header = struct.pack("<4s3I", b"MANI", archive.ovl.version, archive.ovl.flag_2, len(names) )

	# sizedstr data + 3 buffers
	# sized str data gives general info
	# buffer 0 holds all mani infos - weirdly enough, its first 10 bytes come from the sized str data!
	# buffer 1 is list of hashes and zstrs for each bone name
	# buffer 2 has the actual keys
	with open(archive.indir(name), 'wb') as outfile:
		outfile.write(manis_header)
		for mani in names:
			outfile.write(mani.encode()+b"\x00")
		outfile.write(ss_data)
		for buff in sized_str_entry.data_entry.buffers:
			outfile.write(buff.data)
	#
	# for i, buff in enumerate(sized_str_entry.data_entry.buffers):
	# 	with open(archive.indir(name)+str(i), 'wb') as outfile:
	# 		outfile.write(buff.data)
	# if "partials" in name:
		# data = ManisFormat.Data()
		# with open(archive.indir(name), "rb") as stream:
		# 	data.read(stream)

def write_fgm(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	
	try:
		buffer_data = sized_str_entry.data_entry.buffer_datas[0]
		print("buffer size",len(buffer_data))
	except:
		print("Found no buffer data for", name)
		buffer_data = b""
	# for i, f in enumerate(sized_str_entry.fragments):
	# 	with open(archive.indir(name)+str(i), 'wb') as outfile:
	# 		outfile.write( f.pointers[1].data )
	# basic fgms
	if len(sized_str_entry.fragments) == 4:
		tex_info, attr_info, zeros, data_lib  = sized_str_entry.fragments
		len_tex_info = tex_info.pointers[1].data_size
		len_zeros = zeros.pointers[1].data_size
	# no zeros, otherwise same as basic
	elif len(sized_str_entry.fragments) == 3:
		tex_info, attr_info, data_lib  = sized_str_entry.fragments
		len_tex_info = tex_info.pointers[1].data_size
		len_zeros = 0
	# fgms for variants
	elif len(sized_str_entry.fragments) == 2:
		attr_info, data_lib = sized_str_entry.fragments
		len_tex_info = 0
		len_zeros = 0
	else:
		raise AttributeError("Fgm length is wrong")
	# write fgm
	fgm_header = struct.pack("<4s7I", b"FGM ", archive.ovl.version, archive.ovl.flag_2, len(sized_str_entry.fragments), len_tex_info, attr_info.pointers[1].data_size, len_zeros, data_lib.pointers[1].data_size, )

	with open(archive.indir(name), 'wb') as outfile:
		# write custom FGM header
		outfile.write( fgm_header )
		outfile.write( sized_str_entry.pointers[0].data )
		# write each of the fragments
		for frag in sized_str_entry.fragments:
			outfile.write( frag.pointers[1].data )
		# write the buffer
		outfile.write(buffer_data)


def write_materialcollection(archive, sized_str_entry):
	name = sized_str_entry.name.replace("materialcollection", "matcol")
	print("\nWriting",name)
	
	matcol_header = struct.pack("<4s 2I B", b"MATC ", archive.ovl.version, archive.ovl.flag_2, sized_str_entry.has_texture_list_frag )

	with open(archive.indir(name), 'wb') as outfile:
		# write custom matcol header
		outfile.write(matcol_header)

		outfile.write(sized_str_entry.f0.pointers[0].data)
		outfile.write(sized_str_entry.f0.pointers[1].data)
		if sized_str_entry.has_texture_list_frag:
			outfile.write(sized_str_entry.tex_pointer.pointers[0].data)
			for tex in sized_str_entry.tex_frags:
				outfile.write(tex.pointers[1].data)
		
		outfile.write(sized_str_entry.mat_pointer.pointers[0].data)
		for tup in sized_str_entry.mat_frags:
			# write root frag, always present
			m0 = tup[0]
			# the name of the material slot or variant
			outfile.write(m0.pointers[1].data)
			# material layers only: write info and attrib frags + children
			for f in tup[1:]:
				outfile.write(f.pointers[0].data)
				for child in f.children:
					for pointer in child.pointers:
						outfile.write( pointer.data )

	
def write_lua(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	
	try:
		buffer_data = sized_str_entry.data_entry.buffer_datas[0]
		print("buffer size",len(buffer_data))
	except:
		print("Found no buffer data for",name)
		buffer_data = b""
	if len(sized_str_entry.fragments) != 2:
		print("must have 2 fragments")
		return
	# write lua
	with open(archive.indir(name)+".bin", 'wb') as outfile:
		# write the buffer
		outfile.write(buffer_data)
		binfile = outfile.name
	#texconv.bin_to_lua(binfile, archive.dir)
	#with open(archive.indir(name)+"meta", 'wb') as outfile:
		# write each of the fragments
		#print(sized_str_entry.pointers[0].data)
		#outfile.write( sized_str_entry.pointers[0].data )
		#for frag in sized_str_entry.fragments:
			#print(frag.pointers[0].data)
			#print(frag.pointers[1].data)
			#outfile.write( frag.pointers[0].data )
			#outfile.write( frag.pointers[1].data )


def write_assetpkg(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	if len(sized_str_entry.fragments) == 1:
		print(len(sized_str_entry.fragments))
		f_0 = sized_str_entry.fragments[0]
	else:
		print("Found wrong amount of frags for",name)
		return
	with open(archive.indir(name), 'wb') as outfile:
		f_0.pointers[1].strip_zstring_padding()
		outfile.write(f_0.pointers[1].data[:-1])


def write_fdb(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	
	try:
		buff = sized_str_entry.data_entry.buffer_datas[1]
	except:
		print("Found no buffer data for",name)
		return
	
	with open(archive.indir(name), 'wb') as outfile:
		# write the buffer, only buffer 1
		# buffer 0 is just the bare file name, boring
		# sizedstr data is just size of the buffer
		outfile.write(buff)


def write_xmlconfig(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)

	if len(sized_str_entry.fragments) == 1:
		f_0 = sized_str_entry.fragments[0]
	else:
		print("Found wrong amount of frags for",name)
		return
	# write xml
	with open(archive.indir(name), 'wb') as outfile:
		# 8 x b00
		# sized_str_entry.pointers[0].data
		# 8 x b00
		# outfile.write( f_0.pointers[0].data )
		# the actual xml data
		# often with extra junk at the end (probably z str)
		f_0.pointers[1].strip_zstring_padding()
		# strip the b00 zstr terminator byte
		outfile.write( f_0.pointers[1].data[:-1] )


def write_userinterfaceicondata(archive, sized_str_entry):
	name = sized_str_entry.name
	print("\nWriting",name)
	
	try:
		buffer_data = sized_str_entry.data_entry.buffer_datas[0]
		print("buffer size",len(buffer_data))
	except:
		print("Found no buffer data for",name)
		buffer_data = b""
	if len(sized_str_entry.fragments) == 2:
		f_0, f_1 = sized_str_entry.fragments
	else:
		print("Found wrong amount of frags for",name)
		return
	# write xml
	xml_header = struct.pack("<12s5I", b"USERICONDATA", f_0.pointers[0].data_size, f_0.pointers[1].data_size, f_1.pointers[0].data_size, f_1.pointers[1].data_size, len(buffer_data))
	with open(archive.indir(name), 'wb') as outfile:
		# write custom FGM header
		outfile.write(xml_header)
		# write each of the fragments
		for frag in (f_0,f_1):
			outfile.write( frag.pointers[0].data )
			outfile.write( frag.pointers[1].data )
		# write the buffer
		outfile.write(buffer_data)
