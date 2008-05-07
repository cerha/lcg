# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008 Brailcom, o.p.s.
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

The LCG content elements may depend on several external resources.  These resources usually refer
to external files, but in general, thay don't depend on these files, they just provide their
abstract representation.  The resources are maintained by a 'ResourceProvider' instance for each
'ContentNode' instance.
    
"""

import os
import shutil
import codecs
import glob
import textwrap
import config

from lcg import *


class Resource(object):
    """Generic resource class."""
    
    def __init__(self, filename, title=None, descr=None, uri=None):
        super(Resource, self).__init__()
        assert isinstance(filename, (str, unicode)), filename
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        self._filename = filename
        self._title = title
        self._descr = descr
        self._uri = uri or filename
                 
    def filename(self):
        return self._filename
        
    def descr(self):
        return self._descr
        
    def title(self):
        return self._title
            
        self._title = title
        self._descr = descr

    def uri(self):
        return self._uri


class Image(Resource):
    """An image resource."""

    def __init__(self, filename, width=None, height=None, **kwargs):
        super(Image, self).__init__(filename, **kwargs)
        #if width is None or height is None:
        #    import Image as Img
        #    img = Img.open(self._src_path)
        #    width, height = img.size
        self._width = width
        self._height = height
        
    def width(self):
        return self._width
        
    def height(self):
        return self._height
    

class Stylesheet(Resource):
    """A cascading style-sheet."""

class Script(Resource):
    """A java/ecma/... script object used within the content."""

class Media(Resource):
    """Media file, such as audio or video."""

class Flash(Resource):
    """Adobe/Macromedia Flash object."""

    
class ResourceProvider(object):
    """An abstract base class for different resource provider implementations.

    The public methods defined here form the mandatory resource provider interface.
    
    """

    def resources(self, cls=None):
        """Return the list of all resources this node depends on.

        The optional argument 'cls' allows restriction of the returned resources by their type
        (class).
        
        """
        return ()
        
    def resource(self, cls, filename, fallback=True, **kwargs):
        """Get the resource instance by its type and relative filename.

        Arguments:
        
          cls -- resource class.
          
          filename -- filename of the resource.
            
          fallback -- if True, a valid 'Resource' instance will be returned even if the resource
            file doesn't exist.  The problem will be logged, but the program will continue as if
            the resource was there.  If False, None is returned when the resource file doesn't
            exist.

          kwargs -- resource specific constructor arguments.

        """
        return None
    

class StaticResourceProvider(object):
    """Provides resources from a static list passed to the constructor.

    This resource provider is practical when the list of resources is already known in the
    construction time.  It may be for example read from a database etc.
    
    """

    def __init__(self, resources):
        self._resources = resources
        self._dict = None

    def resources(self, cls=None):
        if cls is not None:
            return [r for r in self._resources if isinstance(r, cls)]
        else:
            return self._resources
        
    def resource(self, cls, filename, fallback=False):
        if self._dict is None:
            self._dict = dict([(r.filename(), r) for r in self._resources])
        resource = self._dict.get(filename)
        if not isinstance(resource, cls):
            resource = None
        if resource is None and fallback:
            resource = cls(filename)
        return resource


# ==============================================================================
# IMPORTANT: The classes below are here just for backwards compatibility.  LCG
# was initially only operating on files, thus the instances of resources were
# bound to files and were able to read/write themselves from/to the files.  The
# current model, however, doesn't presume that the resources exist in files and
# thus the new classes defined above only define resource properties and their
# construction and export is left to other components.  The code below should
# be removed -- the resource construction from input files should be
# implemented in a separate layer (which also constructs the content itself)
# and export should be left to the exporter.
# ==============================================================================

class XResource(Resource):
    """Extended resource class.
    
    Instances should not be constructed directly.  Use the
    'ContentNode.resource()' method instead.

    """
    
    SUBDIR = 'resources'
    """The subdirectory, where the resource files are both searched on input
    and stored on output."""

    ALT_SRC_EXTENSIONS = ()
    """A list of alternative source file extensions.  When the input file of
    the same name as passed to the constructor does not exist, other files are
    searched with the same baseneme and all the extensions listed here.  An
    appropriate conversion is possible within the '_export()' method."""
    
    def __init__(self, file, src_path, **kwargs):
        """Initialize the instance.

        Arguments:

          file -- name of the resource file.
          src_path -- source file path.  This is an absolut filename of the source file.  The
            filename of the source file must not necessarily be the same as 'file'.  For examlpe a
            conversion may be involved (depending on particular 'Resource' subclass).
            
        """
        super(XResource, self).__init__(file, **kwargs)
        self._src_path = src_path

    def ok(self):
        return os.path.exists(self._src_path)

    def _dst_path(self):
        return os.path.join(self.SUBDIR, self._filename)
            
    def uri(self):
        return '/'.join(self._dst_path().split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

            
    def _additional_export_condition(self):
        return False

    def _export(self, infile, outfile):
        if os.path.exists(infile): 
            shutil.copyfile(infile, outfile)
            log("%s: file copied.", outfile)

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
            
    def get(self):
        fh = open(self._src_path)
        data = fh.read()
        fh.close()
        return data
            
        
class XMedia(XResource, Media):
    """A media object used within the content."""
    SUBDIR = 'media'
    ALT_SRC_EXTENSIONS = ('.wav',)

    def __init__(self, file, src_path):
        for f in (file, src_path):
            basename, ext = os.path.splitext(f)
            assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" % ext
        super(XMedia, self).__init__(file, src_path)

    def _export(self, infile, outfile):
        input_format = os.path.splitext(infile)[1].upper()[1:]
        output_format = os.path.splitext(outfile)[1].upper()[1:]
        if input_format == output_format:
            return super(XMedia, self)._export(infile, outfile)
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

        
class XStylesheet(XResource, Stylesheet):
    SUBDIR = 'css'

class XImage(XResource, Image):
    SUBDIR = 'images'

class XScript(XResource, Script):
    SUBDIR = 'scripts'

class XFlash(XResource, Flash):
    SUBDIR = 'flash'
    
class XTranscript(XResource):
    """A textual transcript of a recording ."""
    SUBDIR = 'transcripts'

    def __init__(self, file, src_path, text=None, input_encoding='utf-8',
                 **kwargs):
        """Initialize the instance.

        Arguments:
        
          text -- if defined and the source file does not exist, the
            destination file will be created using the specified text as its
            content.

        """
        self._text = text
        self._input_encoding = input_encoding
        super(XTranscript, self).__init__(file, src_path, **kwargs)

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
        text = unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE') + \
               "\n\n".join([textwrap.fill(x) for x in text.replace("\r\n", "\n").split("\n\n")])
        output = open(outfile, 'w')
        try:
            output.write(text.replace('\n', '\r\n').encode('utf-8'))
        finally:
            output.close()
    

# ==============================================================================
# ==============================================================================

class FileResourceProvider(ResourceProvider):
    """Provides resources read from files.
    
    The possible source directories are first searched for the input file:

      * the directory passed as the 'searchdir' argument to the 'resource()' method call,
      * all directories passed as the 'dirs' argument to the provider constructor,
      * default resource directory ('config.default_resource_dir').

    """
    def __init__(self, dirs):
        assert isinstance(dirs, (list, tuple))
        self._dirs = tuple(dirs)
        self._cache = {}
        super(FileResourceProvider, self).__init__()
        
    def _resource(self, cls, file, fallback=True, searchdir=None, **kwargs):
        if not issubclass(cls, XResource):
            assert issubclass(cls, Resource), cls
            return fallback and cls(*args, **kwargs) or None
        dirs = [os.path.join(dir, cls.SUBDIR) for dir in
                self._dirs + (config.default_resource_dir,)]
        if searchdir is not None:
            dirs.insert(0, searchdir)
        basename, ext = os.path.splitext(file)
        altnames = [basename+e for e in cls.ALT_SRC_EXTENSIONS if e != ext]
        for d in dirs:
            for src_file in [file] + altnames:
                src_path = os.path.join(d, src_file)
                if os.path.exists(src_path):
                    return cls(file, src_path, **kwargs)
                elif src_path.find('*') != -1:
                    pathlist = glob.glob(src_path)
                    if pathlist:
                        pathlist.sort()
                        return [cls(os.path.splitext(path[len(d)+1:])[0]+ext,
                                    path, **kwargs) for path in pathlist]
        if fallback:
            result = cls(file, file, **kwargs)
            if not result.ok():
                log("Resource file not found:", file, dirs)
        else:
            result = None
        return result

    def resource(self, cls, file, fallback=True, searchdir=None, **kwargs):
        key = (cls, file, tuple(kwargs.items()))
        try:
            result = self._cache[key]
        except KeyError:
            result = self._resource(cls, file, fallback=fallback, searchdir=searchdir, **kwargs)
            self._cache[key] = result
        return result

    def resources(self, cls=None):
        if cls is None:
            cls = Resource
        result = []
        for r in self._cache.values():
            if isinstance(r, (list, tuple)):
                for rr in r:
                    if isinstance(rr, cls):
                        result.append(rr)
            elif isinstance(r, cls):
                result.append(r)
        return result
    
