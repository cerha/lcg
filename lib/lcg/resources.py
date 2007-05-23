# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

Any 'ContentNode' (or more often a piece of 'Content' within it) can depend on several external
resources.  The resources are maintained by a 'ResourceProvider' instance for each node.
    
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
    
    def __init__(self, file, title=None, descr=None, uri=None, **kwargs):
        super(Resource, self).__init__(**kwargs)
        assert isinstance(file, (str, unicode)), file
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        self._file = file
        self._title = title
        self._descr = descr
        self._uri = uri or file
                 
    def file(self):
        return self._file
        
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

    def __init__(self, file, width=None, height=None, **kwargs):
        super(Image, self).__init__(file, **kwargs)
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
    pass


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
        
    def resource(self, cls, file, fallback=True, **kwargs):
        """Get the resource instance by its type and relative filename.

        Arguments:
        
          cls -- resource class.
          
          file -- filename of the resource.
            
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
        
    def resource(self, cls, file, fallback=False):
        if self._dict is None:
            self._dict = dict([(r.file(), r) for r in self._resources])
        resource = self._dict.get(file) or cls(file)
        return isinstance(resource, cls) and resource or None


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

    SHARED = True
    """A boolean flag indicating that the file may be shared by multiple nodes
    (is not located within the node-specific subdirectory, but rather in a
    course-wide resource directory)."""

    ALT_SRC_EXTENSIONS = ()
    """A list of alternative source file extensions.  When the input file of
    the same name as passed to the constructor does not exist, other files are
    searched with the same baseneme and all the extensions listed here.  An
    appropriate conversion is possible within the '_export()' method."""
    
    def __init__(self, file, src_path, subdir=None, raise_error=False, **kwargs):
        """Initialize the instance.

        Arguments:

          file -- name of the resource file.
          src_path -- source file path.  This is an absolut filename of the source file.  The
            filename of the source file must not necessarily be the same as 'file'.  For examlpe a
            conversion may be involved (depending on particular 'Resource' subclass).
          subdir -- Destination subdirectory name.  This argument is only needed for the resource
            types which are not shared.

        """
        super(XResource, self).__init__(file, **kwargs)
        assert self.SHARED and subdir is None or isinstance(subdir, str)
        self._src_path = src_path
        self._subdir = subdir

    def ok(self):
        return os.path.exists(self._src_path)

    def _dst_path(self):
        if self.SHARED:
            dst_dir = self.SUBDIR
        else:
            dst_dir = os.path.join(self.SUBDIR, self._subdir)
        return os.path.join(dst_dir, self._file)
            
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
            
        
class Media(XResource):
    """A media object used within the content."""
    SUBDIR = 'media'
    SHARED = False
    ALT_SRC_EXTENSIONS = ('.wav',)

    def __init__(self, file, src_path, subdir=None):
        for f in (file, src_path):
            basename, ext = os.path.splitext(f)
            assert ext in ('.ogg','.mp3','.wav'), \
                   "Unsupported media type: %s" % ext
        super(Media, self).__init__(file, src_path, subdir=subdir)

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
    """A shared media object."""
    SHARED = True
    

class Script(XResource):
    """A java/ecma/... script object used within the content."""
    SUBDIR = 'scripts'

    
class XStylesheet(XResource, Stylesheet):
    """A stylesheet used within the content."""
    SUBDIR = 'css'

    
class Transcript(XResource):
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
        super(Transcript, self).__init__(file, src_path, **kwargs)

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

class _FileResourceProvider(ResourceProvider):
    """Resource provider reading the resources from filesystem."""

    _cache = {}

    def __init__(self, dirs, dst_subdir=None):
        assert isinstance(dirs, (list, tuple))
        self._dirs = dirs
        self._dst_subdir = dst_subdir
        super(_FileResourceProvider, self).__init__()
        
    def _resource(self, cls, file, fallback=True, **kwargs):
        dirs = [os.path.join(dir, cls.SUBDIR) for dir in self._dirs]
        if cls.SHARED:
            dirs = [''] + dirs
        else:
            kwargs = dict(subdir=self._dst_subdir)
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
            path = os.path.join(dirs[0], file)
            result = cls(file, path, **kwargs)
            if not result.ok():
                log("Resource file not found:", file, dirs)
        else:
            result = None
        return result

    def resource(self, cls, file, fallback=True, **kwargs):
        key = (cls, file, tuple(kwargs.items()))
        try:
            result = self._cache[key]
        except KeyError:
            result = self._resource(cls, file, fallback=fallback, **kwargs)
            self._cache[key] = result
        return result


class SharedFileResourceProvider(_FileResourceProvider):
    """Provides resources shared by multiple nodes."""
    
    def __init__(self, root_dir):
        dirs = (root_dir, config.default_resource_dir)
        super(SharedFileResourceProvider, self).__init__(dirs)

    def resource(self, *args, **kwargs):
        return self._resource(*args, **kwargs)
    
        
class FileResourceProvider(_FileResourceProvider):
    """Provides resources read from files.
    
    The possible source directories are first searched for the input file:

      * For shared resource types this is the current working directory, course root directory
        and than LCG default resource directory ('config.default_resource_dir') in the
        subdirectory given by the resource type.

      * For other resource types the source files are always expected in source directory (as
        specified by the constructor argument `dir').
    
    """

    _resources = []
    
    def __init__(self, src_dir, dst_subdir, shared_resource_provider):
        self._shared_resource_provider = shared_resource_provider
        super(FileResourceProvider, self).__init__((src_dir,), dst_subdir=dst_subdir)
        
    def _resource(self, cls, *args, **kwargs):
        assert issubclass(cls, Resource), cls
        if not issubclass(cls, XResource):
            return kwargs.get('fallback') and cls(file, **kwargs) or None
        if cls.SHARED:
            result = self._shared_resource_provider.resource(cls, *args, **kwargs)
        else:
            result = super(FileResourceProvider, self)._resource(cls, *args, **kwargs)
        if result is not None:
            if isinstance(result, (tuple, list)):
                resources = result
            else:
                resources = (result,)
            for r in resources:
                if r not in self._resources:
                    self._resources.append(r)
        return result
    
    def resources(self, cls=None):
        if cls is not None:
            return tuple([r for r in self._resources if isinstance(r, cls)])
        else:
            return tuple(self._resources)

    
