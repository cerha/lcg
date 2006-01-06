# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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

def resource(cls, parent, file, fallback=True, **kwargs):
    """Return the resource instance for given ContentNode.

    Arguments:

       cls -- resource class.
       parent -- the ContentNone instance, for which the resource is allocated.
       file -- filename of the resource.
       fallback -- if True, a valid 'Resource' instance will be returned even if
          the resource file doesn't exist.  The problem will be logged, but the
          program will continue as if the resource was there.  If False, None
          is returned when the resource file doesn't exist.
       kwargs -- additional constructor arguments.

    The possible source directories are first searched for the input file:

      * For shared resource types this is the current working directory, course
        root directory and than LCG default resource directory
        ('config.default_resource_dir') in the subdirectory given by the
        resource type.

      * For other media types the source files are always expected in parent
        node's source directory ('ContentNode.src_dir()').
    
    The instances are cached.  Use this function instead of creating the
    instances directly.

    """
    assert issubclass(cls, Resource)
    assert isinstance(parent, ContentNode), \
           "Not a 'ContentNode' instance: %s" % parent
    if not cls.SHARED:
        kwargs['parent'] = parent
    key = (cls, file, tuple(kwargs.items()))
    global _cache
    try:
        return _cache[key]
    except KeyError:
        if cls.SHARED:
            src_dirs = ('',
                        os.path.join(parent.root().src_dir(), cls.SUBDIR),
                        os.path.join(config.default_resource_dir, cls.SUBDIR))
        else:
            src_dirs = (os.path.join(parent.src_dir(), cls.SUBDIR), )
        basename, ext = os.path.splitext(file)
        altnames = [basename+e for e in cls.ALT_SRC_EXTENSIONS if e != ext]
        for d in src_dirs:
            for src_file in [file] + altnames:
                src_path = os.path.join(d, src_file)
                if os.path.exists(src_path):
                    result = cls(file, src_path, **kwargs)
                    _cache[key] = result
                    return result
                elif src_path.find('*') != -1:
                    pathlist = glob.glob(src_path)
                    if pathlist:
                        pathlist.sort()
                        result = [cls(os.path.splitext(path[len(d)+1:])[0]+ext,
                                      path, **kwargs)
                                  for path in pathlist]
                        _cache[key] = result
                        return result
        if fallback:
            result = cls(file, os.path.join(src_dirs[0], file), **kwargs)
            _cache[key] = result
            if not result.ok():
                log("Resource file not found:", file, src_dirs)
        else:
            result = None
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

    ALT_SRC_EXTENSIONS = ()
    
    def __init__(self, file, src_path, parent=None, raise_error=False):
        """Initialize the instance.

        Arguments:

          file -- name of the resource file.
          src_path -- source file path.  This is an absolut filename of the
            source file.  The filename of the source file must not necessarily
            be the same as 'file'.  For examlpe a conversion may be involved
            (depending on particular 'Resource' subclass).
          parent -- parent node.  This argument is only needed for the resource
            types which are not shared.

        """
        assert self.SHARED and parent is None or isinstance(parent, ContentNode)
        self._file = file
        self._src_path = src_path
        self._parent = parent

    def ok(self):
        return os.path.exists(self._src_path)

    def _dst_path(self):
        if self.SHARED:
            dst_dir = self.SUBDIR
        else:
            dst_dir = os.path.join(self.SUBDIR, self._parent.id())
        return os.path.join(dst_dir, self._file)
            
    def url(self):
        return '/'.join(self._dst_path().split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

    def export(self, dir):
        infile = self._src_path
        outfile = os.path.join(dir, self._dst_path())
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
    ALT_SRC_EXTENSIONS = ('.wav',)

    def __init__(self, file, src_path, parent=None):
        for f in (file, src_path):
            basename, ext = os.path.splitext(f)
            assert ext in ('.ogg','.mp3','.wav'), \
                   "Unsupported media type: %s" % ext
        super(Media, self).__init__(file, src_path, parent=parent)

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

    def __init__(self, file, src_path, parent=None, 
                 text=None, input_encoding='utf-8', raise_error=False):
        """Initialize the instance.

        Arguments:
        
          text -- if defined and the source file does not exist, the
            destination file will be created using the specified text as its
            content.

        """
        self._text = text
        self._input_encoding = input_encoding
        super(Transcript, self).__init__(file, src_path, parent=parent,
                                         raise_error=raise_error)

    def ok(self):
        return os.path.exists(self._src_path) or self._text is not None
            
    def _additional_export_condition(self):
        return self._text is not None

    def _export(self, infile, outfile):
        if self._text is not None:
            text = self._text
        elif os.path.exists(infile): 
            fh = codecs.open(infile, encoding=self._input_encoding)
            try:
                text = ''.join(fh.readlines())
            except UnicodeDecodeError, e:
                raise Exception("Error while reading file %s: %s" % (infile, e))
            fh.close()
        else:
            return
        text = "\n\n".join([textwrap.fill(x)
                            for x in text.replace("\r\n", "\n").split("\n\n")])
        output = open(outfile, 'w')
        try:
            output.write(text.encode('utf-8'))
        finally:
            output.close()
            
