# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Representation of external resources.

Any 'ContentNode' (or more often a piece of 'Content' within it) can depend on
several external resources.  They are maintained by parent 'ContentNode' so
that the node is able to keep track of all the resources it depends on.
    
"""

import os
import shutil
import codecs
import glob

from lcg import *

_cache = {}

def resource(cls, parent, file, **kwargs):
    """Return the resource instance for given ContentNode.

    Arguments:

       cls -- resource class.
       parent -- the ContentNone instance, for which the resource is allocated.
       file -- filename of the resource
       kwargs -- constructor arguments which should be passed after the
         'src_path' and 'dst_path' arguments.

    The possible source directories are first searched for the input file:

      * For shared resource types this is the current working directory, course
        root directory and than LCG default resource directory
        ('config.default_resource_dir') in the subdirectory given by the
        resource type.

      * For other media types the source files are always expected in parent
        node's source directory ('ContentNode.src_dir()').
    
    The instances are cached properly, so it is recommended to use this
    function instead of creating the instances directly.

    """
         
    assert issubclass(cls, Resource)
    assert isinstance(parent, ContentNode), \
           "Not a 'ContentNode' instance: %s" % parent
    key = (cls, file, tuple(kwargs.items()))
    if not cls.SHARED:
        key = (parent, ) + key
    global _cache
    try:
        return _cache[key]
    except KeyError:
        if cls.SHARED:
            src_dirs = ('',
                        os.path.join(parent.root().src_dir(), cls.SUBDIR),
                        os.path.join(config.default_resource_dir, cls.SUBDIR))
            dst_dir = cls.SUBDIR
        else:
            src_dirs = (os.path.join(parent.src_dir(), cls.SUBDIR), )
            dst_dir = os.path.join(cls.SUBDIR, parent.subdir())
        for d in src_dirs:
            src_path = os.path.join(d, file)
            dst_path = os.path.join(dst_dir, file)
            if os.path.exists(src_path):
                result = cls(src_path, dst_path, **kwargs)
                _cache[key] = result
                return result
            elif src_path.find('*') != -1:
                pathlist = glob.glob(src_path)
                if pathlist:
                    r = [cls(src_path, dst_dir + src_path[len(d):], **kwargs)
                         for src_path in pathlist]
                    _cache[key] = r
                    return r
        result = cls(os.path.join(src_dirs[0], file), dst_path, **kwargs)
        _cache[key] = result
        return result

  
class Resource(object):
    """Base resource class.
    
    Instances should not be constructed directly.  Use the
    'ContentNode.resource()' method instead.

    """
    SUBDIR = 'resources'
    SHARED = True
    """A boolean flag indicating that the file may be shared by multiple nodes
    (is not located within the node-specific subdirectory, but rather in a
    course-wide resource directory)."""
    
    def __init__(self, src_path, dst_path):
        """Initialize the instance.

        Arguments:

          src_path -- source file path.
          dst_path -- destination file path.

        """
        self._src_path = src_path
        self._dst_path = dst_path
        if self._needs_source_file() and not os.path.exists(src_path):
            log("Resource file not found:", src_path)

    def _needs_source_file(self):
        return True
        
    def url(self):
        return '/'.join(self._dst_path.split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

    def export(self, dir):
        infile = self._src_path
        outfile = os.path.join(dir, self._dst_path)
        if (not os.path.exists(outfile)
            or (os.path.exists(infile) and
                os.path.getmtime(outfile) < os.path.getmtime(infile))
            or self._additional_export_condition()):
            if not os.path.isdir(os.path.dirname(outfile)):
                os.makedirs(os.path.dirname(outfile))
            self._export(infile, outfile)
            
    def _additional_export_condition(self):
        return False

    def _export(self, infile, outfile):
        if os.path.exists(infile): 
            shutil.copyfile(infile, outfile)
            log("%s: file copied.", outfile)
            

    def get(self):
        fh = open(self._src_path)
        data = fh.read()
        fh.close()
        return data
            

        
class Media(Resource):
    """Representation of a media object used within the content."""
    SUBDIR = 'media'
    SHARED = False

    def __init__(self, src_path, dst_path):
        basename, ext = os.path.splitext(src_path)
        assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" % ext
        super(Media, self).__init__(src_path, dst_path)

    def _export(self, infile, outfile):
        input_format = os.path.splitext(infile)[1].upper()[1:]
        output_format = os.path.splitext(outfile)[1].upper()[1:]
        if input_format == output_format:
            return super(Media, self)._export(infile, outfile)
        elif input_format != 'WAV':
            raise Exception("Unsupported conversion: %s -> %s" % \
                            (input_format, output_format))
        var = 'LCG_%s_COMMAND' % output_format
        def cmd_err(msg):
            raise Exception(msg % var + "\n" +
                            "Specify a command encoding a wave file '%%infile' "
                            "to an %s file '%%outfile'." % output_format)
        try:
            cmd = os.environ[var]
        except KeyError:
            cmd_err("Environment variable %s not set.")
        if cmd.find("%infile") == -1 or cmd.find("%outfile") == -1:
            cmd_err("Environment variable %s must refer to "
                    "'%%infile' and '%%outfile'.")
        log("%s: converting to %s: %s", outfile, output_format, cmd)
        command = cmd.replace('%infile', infile).replace('%outfile', outfile)
        if os.system(command):
            raise IOError("Subprocess returned a non-zero exit status.")
        

class SharedMedia(Media):
    SHARED = True
        

class Script(Resource):
    """Representation of a script object used within the content."""
    SUBDIR = 'scripts'

    
class Stylesheet(Resource):
    """Representation of a stylesheet used within the content."""
    SUBDIR = 'css'

    
class Image(Resource):
    """Representation of an image used within the content."""
    SUBDIR = 'images'

    
class Transcript(Resource):
    """Representation of a textual recording transcript."""
    SUBDIR = 'transcripts'
    SHARED = False

    def __init__(self, src_path, dst_path, text=None, input_encoding='utf-8'):
        """Initialize the instance.

        Arguments:
        
          src_path, dst_path -- see 'Resource.__init__()'.
          text -- if defined and the source file does not exist, the
            destination file will be created using the specified text As its
            content.

        """
        self._text = text
        self._input_encoding = input_encoding
        super(Transcript, self).__init__(src_path, dst_path)

    def _needs_source_file(self):
        return self._text is None
            
    def _additional_export_condition(self):
        return self._text is not None

    def _export(self, infile, outfile):
        if self._text is not None:
            text = self._text
        else:
            fh = codecs.open(infile, encoding=self._input_encoding)
            try:
                text = ''.join(fh.readlines())
            except UnicodeDecodeError, e:
                raise Exception("Error while reading file %s: %s" % (infile, e))
            fh.close()
        text = "\n\n".join([textwrap.fill(x)
                            for x in text.replace("\r\n", "\n").split("\n\n")])
        output = open(outfile, 'w')
        try:
            output.write(text.encode('utf-8'))
        finally:
            output.close()
