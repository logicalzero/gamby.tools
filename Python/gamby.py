#!/usr/bin/env python

"""
GAMBY Graphics Tool
~~~~~~~~~~~~~~~~~~~

Part of the GAMBY toolset: https://github.com/logicalzero/gamby.tools

This package contains methods for converting GIF images into code for use
with the GAMBY LCD/Game shield. This script also functions as a stand-alone
utility which can be run from the command line.

@todo: Further code cleaning. Too many hacks; full refactoring may be needed.
    Data type in generated code may not be consistent.
@todo: Create multi-frame sprites
@todo: Add 'icons' (8px high bitmaps; same as sprites without height)
@todo: Add 'splash pages' (multi-line icons)
@todo: Remove comments before converting code back to images.
@todo: Use getopt or argparse instead of 'manually' parsing arguments; there
    are now too many options to continue as is.

@var _SIZE_LIMITS: An set of 'constants' for providing warnings when too much
    memory is being used.
@type _SIZE_LIMITS: A list of tuples containing a size (in bytes) and a
    corresponding warning message.
    
"""

import os
import sys
import string

# Ensure a compatible version of Python is being used
# (the ternary operator was added in 2.5)

if sys.version[:3] < '2.5':
   if __name__ == "__main__":
      print "This script requires Python version 2.5 or greater."
      exit(1)
   raise RuntimeError("Python version 2.5 or greater required")


# Ensure PIL (or Pillow, etc.) is installed

try:
   import Image, ImageSequence
except ImportError, e:
   try:
      from PIL import Image, ImageSequence
   except ImportError, e:
      if __name__ == "__main__":
         print "The Python Imaging Library (PIL) or Pillow is required " \
          "for this tool to work."
         exit(1)
      raise e


##############################################################################

# TODO: Subtract worst-case bootloader (and GAMBY library) sizes from max
_SIZE_LIMITS = [
   (30 * 1024, "ATMega328 available flash"),
   (14 * 1024, "ATMega168 available flash"),
   (12 * 1024, "a reasonable size"),
]

##############################################################################

class ConversionError(Exception):
    pass

##############################################################################

def fixName(name):
   """ Create a reasonable variable name from a filename.
   """
   name = os.path.splitext(os.path.split(name)[-1])[0]
   if len(name) == 0:
       return "no_name"
   for c in (string.punctuation + string.whitespace):
       name = name.replace(c, '_')
   if name[0].isdigit():
      name = '_' + name
   return name.rstrip('_').replace('__', '_')

##############################################################################
   
class Sprites:
    """
    A class representing the namespace for all GAMBY sprite conversion code.
    Do not instantiate; just call the class' methods directly.
    
    @cvar _useMask: The default setting for whether GIF image transparency
        should be used to generate a second 'mask' sprite.
    @cvar _dataType: The name of the Arduino data type to use when generating
        code.
    @cvar _unitSize: The number of bits per unit of data.
    """ 

    _useMask = True
    _dataType = 'prog_uchar'
    _unitSize = 8
   
    @classmethod
    def numFrames(cls, img):
        """ Return the number of frames in an animated GIF.

            @param img: The image to count
            @type img: `Image.Image`
            @return: The frame count
        """
        i = 1
        img.seek(0)
        try:
            while True:
                img.seek(img.tell() + 1)
                i += 1
        except EOFError:
            pass
        img.seek(0)
        return i


    @classmethod
    def createData(cls, img, ignoreSolid=True):
        """ Turn an image into an array of bits, stored as a series of bytes.
            The first two items are the image dimensions.

            @param img: The image from which to generate the data
            @type img: `Image.Image`
            @param ignoreSolid: If `True`, bitmaps that are all black or
                all white are ignored; `None` is returned.
        """
        if img is None:
            return None
        if img.mode == '1':
            data = img.getdata()
        else:
            data = img.convert('1').getdata()
        if ignoreSolid:
            s = sum(data)
            if s == 0:
                # Totally black, ignore
                return None
            if s == img.size[0] * img.size[1] * 255:
                # Totally white, ignore
                return None

        # Make the data list. The first two elements are the dimension
        result = list(img.size)

        i = 0
        b = 0
        for p in data:  
            # bitmaps on LCD are 'inverse': 1 is black, 0 is not
            p = 0 if p else 1
            b = (b << 1) + p
            i += 1
            if i == cls._unitSize:
                result.append(b)
                i = 0
                b = 0
        return result


    @classmethod
    def undo(cls, d, imgSize=None):
        """ Convert an array of bitmap data into an image.
        """
        if imgSize == None:
            imgSize = d[0:2]
            d = d[2:]
        img = Image.new('1', imgSize, 255)
        ar = []
        for b in d:
            for c in bin(b)[2:].rjust(cls._unitSize, '0'):
                if c == '0':
                    ar.append(255)
                else:
                    ar.append(0)
        img.putdata(ar)
        return img.rotate(90)


    @classmethod
    def writeCode(cls, name, data, digits=2, sizes=True, tab="    "):
        """ Generate Arduino code from a single list of bitmap data.
        """
        if data == None:
            return ''
        result = []
        if sizes:
            result.append("%s%s, %s," % (tab, data[0], data[1]))
         
        line = []
        i = 0
        for b in data[2:]:
            if i % 12 == 0:
                line.append("\n%s" % tab)
            line.append("0x%s, " % hex(b)[2:].rjust(digits, '0'))
            i += 1
        result.append(''.join(line).rstrip(' \n,'))
        return "PROGMEM %s %s[] = {\n%s\n}\n" % (cls._dataType, name, '\n'.join(result))


    @classmethod
    def convert(cls, f, mask=None, size=[0, 0]):
        """ Turn an image into Arduino code for GAMBY. Any transparency
            or alpha channel is turned into its own sprite.

            @param f: The image file or filename to convert
            @param mask: If `True` (default), additional sprites are created
                from the image's transparency information.
            @param size: A two element list containing the total number of
                converted images and the total number of bytes they consume.
                This is modified 'in place'.
            @param out: A stream to which to write the results.
        """
        if mask == None:
            mask = cls._useMask
        if isinstance(f, basestring):
            filename = f
            img = Image.open(f)
        elif isinstance(f, Image.Image):
            filename = f.filename
            img = f
        else:
            # Problem.
            raise IOError, "Can't convert %s (not filename or Image.Image)" % f

        totalSize = 0
        bits = []
        for frame in ImageSequence.Iterator(img):
            # image rotated 90 degrees clockwise so bits in best order for LCD
            # (doesn't matter in graphics mode, but in text/block mode it helps)
            img = img.rotate(-90)
            alpha = None
            if mask:
                # Get alpha for mask, using img converted to RGBA
                alpha = Image.new('L', img.size)
                alpha.putdata([x[-1] for x in img.convert("RGBA").getdata()])
            converted = (cls.createData(img), cls.createData(alpha))
            if converted[0]:
                totalSize += len(converted[0])
            bits.append(converted)

        name = fixName(filename)
        result = []
        if not bits:
            # Nothing returned (empty list or possibly None)
            raise ConversionError, "Could not convert %s (no data?)" % filename

        if len(bits) == 1:
             result = [cls.writeCode(name, bits[0][0]),
                       cls.writeCode(name + "_mask", bits[0][1])]
        else:
            for i in range(len(bits)):
                result.append(cls.writeCode("%s_%s" % (name, i), bits[i][0]))
                result.append(cls.writeCode("%s_%s_mask" % (name, i), bits[i][1]))

        if size:
            # Image count and total size (in bytes), modified 'in place'
            size[0] += len(bits)
            size[1] += totalSize

        return '\n'.join(result)


    @classmethod
    def convertFiles(cls, filenames, size=None, mask=None, out=sys.stdout):
        """
        """
        if isinstance(out, basestring):
            out = file(out, 'w')
        for filename in filenames:
            out.write(cls.convert(filename, mask=mask, size=size))
            out.write('\n')
        if out != sys.stdout:
            out.close()
         

    @classmethod
    def unconvert(cls, data, size=None, out=None):
        """ Convert Arduino code back into images.
        """
        # TODO: Put alpha back into GIF?
        # TODO: Remove comments?
        result = []
        start, end = (data.find('prog_uchar'), data.find('}'))
        # Why am I doing this? It was probably modified for a test, but what?
        while start > -1 and start > -1:
            name = data[start + 10:data.find('[]', start)].strip()
            bytes = [b.strip(',') for b in data[data.find('{', start) + 1:end].split()]
            bits = [int(bytes[0]), int(bytes[1])]
            for b in bytes[2:]:
                bits.append(int(b, 16))
            result.append((name, cls.undo(bits)))
            end += 1
            start, end = (data.find('prog_uchar', end), data.find('}', end))

        return result


    @classmethod
    def unconvertFiles(cls, filenames, size=None, out=''):
        """
        """
        images = []
        for filename in filenames:
            f = file(filename, 'r')
            images.append(cls.unconvert(f.read()))
            f.close()
        # do the write here.
        # XXX: Write this!


##############################################################################

class Tilesets(Sprites):
    """
    Methods for generating Gamby tilesets from image data. Tiles are 16-bit
    integers representing a 4x4 pixel square; a tileset consists of 16 tiles.
    The source file is expected to be a 16x16 image containing a 4x4 grid of
    tiles.
    """

    _useMask = False
    _dataType = "prog_uint16_t"
    _unitSize = 16

    @classmethod
    def convert(cls, f, size=None):
        if isinstance(f, basestring):
            filename = f
            img = Image.open(f)
        elif isinstance(f, Image.Image):
            filename = f.filename
            img = f
        else:
            # Problem.
            raise IOError, "Can't convert %s (not filename or Image.Image)" % f

        # image rotated 90 degrees clockwise so bits in best order for LCD
        # (doesn't matter in graphics mode, but in text/block mode it helps)
        img = img.rotate(-90)
        img = img.convert('1')
      
        totalSize = 0
        bits = []
        for c in range(12, -1, -4):
            for r in range(0, 16, 4):
                tile = img.crop((r, c, r + 4, c + 4))
                data = cls.createData(tile)
                bits.append(data)
            
        name = fixName(filename)

        if not bits:
            # Nothing returned (empty list or possibly None)
            raise ConversionError, "Could not convert %s (no data?)" % filename
        
        if size:
            # Image count and total size (in bytes), modified 'in place'
            size[0] += 1
            size[1] += len(bits) * 2
         
        return cls.writeCode(name, bits, digits=cls._unitSize, sizes=False)
      

    def unconvert(*args, **kwargs):
        raise NotImplementedError, "unconvert for Tilesets not yet implemented."


##############################################################################

if __name__ == '__main__':
    argv = sys.argv
    out = sys.stdout
    err = sys.stderr
    scriptName = argv.pop(0)
   
    if argv[0].lower() in ('help', '-h', '--help', '?'):
        print """GAMBY Graphics Tool\n
Usage:
gamby.py <sprite|tileset> [-u|--undo] [-o|--output filename] [sourcefiles]

  sprite: Generates PROGMEM code from an image file. Each frame of an animated
    GIF is converted to its own sprite. Mask sprites are generated from GIF
    transparency.
  tileset: Generates PROGMEM code for a tile-mode tileset from a 4x4 grid of
    4x4 pixel tiles. 

Options:
  sourcefiles: One or more source files to convert. Defaults to stdin.
  --output | -o <filename>: Specifies a file to which the output is to be
    written. Defaults to stdout (for redirecting, etc.).
  --undo | -u: Converts Arduino PROGMEM code back to an image (if possible).
"""
        exit(0)

    params = {}
   
    # Parse out command-line parameters
    # options list: name long form, short form, number of arguments
    options = [
               ('--output', '-o', 1),
               ('--undo', '-u', 0)
    ]
    for longName, shortName, numArgs in options:
        i = -1
        if longName in argv:
            i = argv.index(longName)
            argv[argv.index(longName)] = shortName
        elif shortName in argv:
            i = argv.index(shortName)
        if i >= 0:
            argv.pop(i)
            params[shortName] = [argv.pop(i) for p in range(numArgs)]

    # Process univerally-applicable parameters
    out = params['-o'][0] if '-o' in params else out
    direction = 1 if '-u' in params else 0
   
#   if '-o' in params:
#      out = params['-o'][0]

    # With parameters and script name removed, are there enough arguments?
    if len(argv) == 0:
        err.write('%s: Too few arguments\n' % scriptName)
        if out != sys.stdout:
            out.close()
        if err != sys.stderr:
            err.close()
        exit()
      
    mode = argv.pop(0).lower()

    # List of modes.
    # { <mode name>: (<converter method>, <unconverter method>), ... }
    # <converter> and <unconverter> are functions/methods for generating data from
    # from images and regenerating images from data, respectively. If one is None,
    # the process is one-way. 
    modes = {
             'sprite': (Sprites.convertFiles, Sprites.unconvertFiles),
             'tileset': (Tilesets.convertFiles, None),
    }

    if mode not in modes:
        err.write("%s: unknown command '%s'\n" % (scriptName, mode))
        exit()

    if modes[mode][direction] == None:
        if direction == 0:
            err.write("%s: cannot convert to '%s'\n" % (scriptName, mode))
        else:
            err.write("%s: cannot undo conversion '%s'\n" % (scriptName, mode))
        exit()

    # List to keep track of number of converted items and total size in bytes
    # This gets passed to conversion methods and is changed 'in place'.
    size = [0, 0]

    # Do the conversion!
    modes[mode][direction](argv, size=size, out=out)

    # Give warning if too much data generated.
    for memory, name in _SIZE_LIMITS:
        if size[1] > memory:
            err.write("Warning: Generated data is %s bytes; %s is %s bytes\n" \
                      % (size[1], name, memory))
        break

    # shut things down.
    if out != sys.stdout:
        out.close()
    if err != sys.stderr:
        err.close()
