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
@todo: Sprites.convert() is too big; break into smaller pieces that subclasses
    can override piecemeal. 

@todo: Add option to fill out Icons that are shorter than 8px (including 
    Splashscreens with a short final row), filling extra with 0 or 1.
@todo: Add option to crop Icons that are not divisible by 8.
@todo: Get 'undo' working again, if it seems worthwhile.
@todo: Use regex to parse code when converting back to GIF. This should make it
    easy to do things like remove comments, parse out names, etc.

@var SIZE_LIMITS: An set of 'constants' for providing warnings when too much
    memory is being used.
@type SIZE_LIMITS: A list of tuples containing a size (in bytes) and a
    corresponding warning message.
    
"""

import argparse
import os
import sys
import string
import textwrap

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

SIZE_LIMITS = [
   (30 * 1024, "All ATMega328 available flash, +/- 1KB"),
   (14 * 1024, "ATMega168 available flash (or half ATMega328), +/- 1KB"),
   (12 * 1024, "a reasonable size"),
]

##############################################################################

class ConversionError(Exception):
    """ An exception raised when an image could not be converted to a
        GAMBY bitmap. Improves exception handling when using gamby.py as a 
        library.
    """
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
    def openImage(cls, f):
        """ Load and perform basic validation of an image before conversion. 
            Can be called with either the filename of an image or an 
            `Image.Image`; in the latter case, only the validation is
            performed.
            
            @raise ConversionError: The image failed validation.
            @raise IOError: The image could not be read (or it was neither
                a filename nor `Image.Image`).
            
            @param f: An image, or an image's filename.
            @type f: `Image.Image` or string.
            @rtype: `Image.Image`
        """
        if isinstance(f, basestring):
            return Image.open(f)
        elif isinstance(f, Image.Image):
            return f
        # Problem.
        raise IOError, "Can't convert %s (not filename or Image.Image)" % f
        
        
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
    def getAlpha(cls, img):
        """ Retrieve an image's alpha.
        
            @param img: The image, presumably one with an alpha.
            @type img: `Image.Image`
            @return: A grayscale (mode "L") `Image.Image`
        """
        # Get alpha for mask, using img converted to RGBA
        alpha = Image.new('L', img.size)
        alpha.putdata([x[-1] for x in img.convert("RGBA").getdata()])
        return alpha


    @classmethod
    def createData(cls, img, ignoreSolid=True, sizes=True):
        """ Turn an image into an array of bits, stored as a series of bytes.
            The first two items are the image dimensions.

            @param img: The image from which to generate the data
            @type img: `Image.Image`
            @param ignoreSolid: If `True`, bitmaps that are all black or
                all white are ignored; `None` is returned.
            @return: A list containing [<width>,<height>, [<frame1 bytes...>],
                ..., [<frameN bytes...>]]
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

        result = []
        if sizes:
            # Make the data list. The first two elements are the dimension
            result.extend(img.size)

        i = 0
        b = 0
        for p in data:  
            # bitmaps on LCD are 'inverse': 1 is black, 0 is not
            b = (b << 1) + (0 if p else 1)
            i += 1
            if i == cls._unitSize:
                result.append(b)
                i = b = 0
        return result


    @classmethod
    def undo(cls, d, imgSize=None):
        """ Convert an array of bitmap data into an image.
            Does not (currently) work on multi-frame bitmaps.
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
        img.putdata(ar[:imgSize[0]*imgSize[1]])
        return img.rotate(90)


    @classmethod
    def writeCode(cls, name, data, digits=2, sizes=True, width=78, tab="    "):
        """ Generate Arduino code from a single list of bitmap data.
        """
        if data == None:
            return ''
        lineWidth = width - tab.count(" ") + tab.count("\t") * 4
        result = ["PROGMEM %s %s[] = {" % (cls._dataType, name)]
        if sizes:
            result.append("%s, %s," % (data[0], data[1]))
        for i in xrange(len(data)-2):
            result.append("// Frame %d" % (i))
            result.extend(textwrap.wrap(", ".join(map(hex, data[i+2]))+",", 
                                        lineWidth))
        
        return ('\n'+tab).join(result)[:-1]+"\n};\n"


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
        mask = cls._useMask if mask is None else mask
        
        img = cls.openImage(f)
        filename = img.filename
        
        numFrames = cls.numFrames(img)
        totalSize = 0
        bits = list(img.size)
        alphaBits = list(img.size)
        
        for frame in ImageSequence.Iterator(img):
            # image rotated 90 degrees clockwise so bits in best order for LCD
            # Currently doesn't matter in graphics mode, but bitmaps in text/block mode it helps)
            frame = frame.rotate(-90)
            alpha = cls.getAlpha(frame) if mask else None
            
            converted = cls.createData(frame, ignoreSolid=False, sizes=False)
            bits.append(converted)
            totalSize += len(converted)
            
            if mask:
                convertedAlpha = cls.createData(alpha, ignoreSolid=False, 
                                                sizes=False)
                alphaBits.append(convertedAlpha)
                totalSize += len(convertedAlpha)

        if not bits:
            # Nothing returned (empty list or possibly None)
            raise ConversionError, "Could not convert %s (no data?)" % filename

        name = fixName(filename)
        result = ["// Converted from %s" % filename,]
        result.append(cls.writeCode(name, bits))
        if mask:
            result.append(cls.writeCode(name + "_mask", alphaBits))

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

    def openImage(cls, f):
        """ Perform basic validation of an image before conversion. Raises
            a `ConversionError` if the validation fails; does nothing if 
            validation passes.
        """
        img = Sprites.openImage(f)
        if img.size[0] != 16 or img.size[1] != 16:
            raise ConversionError, "Tilesets must be 16x16; %s is %s" % \
                (img.filename, img.size)
        return img
                

    @classmethod
    def convert(cls, f, mask=None, size=None):
        img = cls.openImage(f)
        filename = img.filename
                
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
                bits.append(data[2])
            
        name = fixName(filename)

        if not bits:
            # Nothing returned (empty list or possibly None)
            raise ConversionError, "Could not convert %s (no data?)" % filename
        
        if size:
            # Image count and total size (in bytes), modified 'in place'
            size[0] += 1
            size[1] += len(bits) * 2
         
        return cls.writeCode(name, bits, digits=cls._unitSize, sizes=False)


    @classmethod
    def unconvert(*args, **kwargs):
        raise NotImplementedError, "unconvert for Tilesets not yet implemented."


##############################################################################

class Icons(Sprites):
    """
    """

    _useMask = False
    
    @classmethod
    def openImage(cls, f):
        """ Loads and validates an image. 

            @raise ConversionError: The image is not a size compatible with
                conversion (height other than 8px).
            @param f: A filename or `Image.Image`
            @rtype: `Image.Image`
        """
        img = Sprites.openImage(f)
        if img.size[1] != 8:
            raise ConversionError, "Icons must be 8px high; %s is %d" % \
                (img.filename, img.size[1])
        return img
                
        
    
    @classmethod
    def writeCode(cls, name, data, digits=2, sizes=True, width=78, tab="    "):
        """ Generate Arduino code from a single list of bitmap data.
        """
        if data == None:
            return ''
        lineWidth = width - tab.count(" ") + tab.count("\t") * 4
        result = ["PROGMEM %s %s[] = {" % (cls._dataType, name)]
        if sizes:
            result.append("%s," % data[0])
        for i in xrange(len(data)-2):
            result.append("// Frame %d" % (i))
            result.extend(textwrap.wrap(", ".join(map(hex, data[i+2]))+",", 
                                        lineWidth))
        
        return ('\n'+tab).join(result)[:-1]+"\n};\n"

    @classmethod
    def unconvert(*args, **kwargs):
        raise NotImplementedError, "unconvert for Icons not yet implemented."


##############################################################################

class Splashscreens(Icons):
    """ Create 'splash screens,' large images split into multiple 8-pixel-high 
        icons, each row stored as a 'frame.' 
    """

    @classmethod
    def openImage(cls, f):
        """ Perform basic validation of an image before conversion. Raises
            a `ConversionError` if the validation fails; does nothing if 
            validation passes.
        """
        img = Sprites.openImage(f)
        if img.size[1] % 8 != 0:
            raise ConversionError, \
                "Icons must be a multiple of 8px high; %s is %d" % \
                (img.filename, img.size[1])
        return img


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
        img = cls.openImage(f)
        filename = img.filename
        
        numFrames = cls.numFrames(img)
        totalSize = 0
        bits = list(img.size)
        
        img = img.rotate(-90)
        for r in xrange(img.size[0]-8, -1, -8):
            thisRow = img.crop((r, 0, r + 8, img.size[1]))
            converted = cls.createData(thisRow, ignoreSolid=False, sizes=False)
            bits.append(converted)
            totalSize += len(converted)
            
        if not bits:
            # Nothing returned (empty list or possibly None)
            raise ConversionError, "Could not convert %s (no data?)" % filename

        name = fixName(filename)
        result = ["// Converted from %s" % filename,]
        result.append(cls.writeCode(name, bits))

        if size:
            # Image count and total size (in bytes), modified 'in place'
            size[0] += len(bits)
            size[1] += totalSize

        return '\n'.join(result).replace("// Frame ", "// Row ")


    @classmethod
    def unconvert(*args, **kwargs):
        raise NotImplementedError, \
            "unconvert for Splashscreens not yet implemented."


##############################################################################


if __name__ == '__main__':
    # List of modes.
    # { <mode name>: (<converter method>, <unconverter method>), ... }
    # <converter> and <unconverter> are functions/methods for generating data from
    # from images and regenerating images from data, respectively. If one is None,
    # the process is one-way. 
    modes = {
             'sprite': Sprites,
             'icon': Icons,
             'splash': Splashscreens,
             'tileset': Tilesets,
    }

    parser = argparse.ArgumentParser(description="GAMBY Graphics Tool.\n"\
        "Converts images into GAMBY data. For best results, images should be" \
        "1-bit (black and white); GIF or PNG8 are recommended.")
    parser.add_argument("mode",
        help="The name of the mode.", choices=modes.keys())
    parser.add_argument("--output", "-o", 
        help="The output filename. Defaults to stdout.")
#    parser.add_argument("--crop", "-c", action="store_true",
#        help="Crop an Icon or Splashscreen's vertical size to a multiple of " \
#            "8 (or just 8 for Icons).")
#    parser.add_argument("--fill", "-f", type=int,
#        help="Fill an Icon or Splashscreen's vertical size to the next " \
#            "multiple of 8, using the specified value (0 or 1).")
    parser.add_argument("--undo", "-u", action="store_true",
        help="Convert code back into an image. Not implemented for all " \
            "formats.")
#    parser.add_argument("--nomask", "-n", action="store_true", default=False,
#        help="Do not generate a 'mask' Sprite from the image's transparency " \
#            "(Sprites only).")
    parser.add_argument("source", nargs="*", help="The source filename(s).")
    args = parser.parse_args()

    err = sys.stderr

    # Process universally-applicable parameters
    out = file.open(args.output,"wb") if args.output else sys.stdout
   
    # List to keep track of number of converted items and total size in bytes
    # This gets passed to conversion methods and is changed 'in place'.
    size = [0, 0]

    # Do the conversion!
    if args.undo:
        try:
            modes[args.mode].unconvertFiles(args.source, out=out)
        except NotImplementedError:
            err.write("Error: undo not implemented for mode '%s'\n" % args.mode)
    else:
        modes[args.mode].convertFiles(args.source, size=size, out=out)


    # Give warning if too much data generated.
    for memory, name in SIZE_LIMITS:
        if size[1] > memory:
            err.write("Warning: Generated data is %s bytes; %s is %s bytes\n" \
                      % (size[1], name, memory))
        break


    # shut things down.
    if out != sys.stdout:
        out.close()
    if err != sys.stderr:
        err.close()
