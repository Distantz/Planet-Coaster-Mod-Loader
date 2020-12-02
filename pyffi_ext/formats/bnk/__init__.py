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
        i = s.find(p, i + 1)


class BnkFormat(pyffi.object_models.xml.FileFormat):
    """This class implements the Ms2 format."""
    xml_file_name = 'bnk.xml'
    # where to look for ms2.xml and in what order:
    # MS2XMLPATH env var, or Ms2Format module directory
    xml_file_path = [os.getenv('BNKXMLPATH'), os.path.dirname(__file__)]
    # file name regular expression match
    RE_FILENAME = re.compile(r'^.*\.bnk$', re.IGNORECASE)
    # used for comparing floats
    _EPSILON = 0.0001

    # basic types
    int = pyffi.object_models.common.Int
    uint64 = pyffi.object_models.common.UInt64
    int64 = pyffi.object_models.common.Int64
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
        """A class to contain the actual Ms2 data."""

        def __init__(self):
            self.version = 0
            self.header = BnkFormat.AuxFileContainer()

        def inspect_quick(self, stream):
            """Quickly checks if stream contains DDS data, and gets the
            version, by looking at the first 8 bytes.

            :param stream: The stream to inspect.
            :type stream: file
            """
            pos = stream.tell()


        # overriding pyffi.object_models.FileFormat.Data methods

        def inspect(self, stream):
            """Quickly checks if stream contains DDS data, and reads the
            header.

            :param stream: The stream to inspect.
            :type stream: file
            """
            pos = stream.tell()
            try:
                self.header.read(stream, data=self)
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
            self.inspect(stream)
            print(self.header)
