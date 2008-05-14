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
    
    SUBDIR = None
    """Name of the subdirectory where files are searched on input and stored on output."""
    
    def __init__(self, filename, title=None, descr=None, uri=None):
        super(Resource, self).__init__()
        assert isinstance(filename, (str, unicode)), filename
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert uri is None or isinstance(uri, (str, unicode)), uri
        self._filename = filename
        self._title = title
        self._descr = descr
        self._uri = uri
                 
    def filename(self):
        return self._filename
        
    def title(self):
        return self._title
            
    def descr(self):
        return self._descr
        
    def uri(self):
        return self._uri


class Image(Resource):
    """An image resource."""
    SUBDIR = 'images'

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
    SUBDIR = 'css'

class Script(Resource):
    """A java/ecma/... script object used within the content."""
    SUBDIR = 'scripts'

class Media(Resource):
    """Media file, such as audio or video."""
    SUBDIR = 'media'

class Flash(Resource):
    """Adobe/Macromedia Flash object."""
    SUBDIR = 'flash'

class XResource(Resource):
    """Exportable resource.
    
    This class extends the resource with an information about the location of the source file for
    the resource.  This source file is normally located by the resource provider, so it is not
    recommended to create the instances directly.  Use the appropriate resource provider class
    (such as 'FileResourceProvider') which is responsible for locating the source file and passing
    the 'src_file' constructor argument to the resource constructor automatically.

    When an 'XResource' instance is found in node's dependencies, the exporter is than able to
    export the resource to the output since the input file is known.

    """
    
    def __init__(self, filename, src_file=None, **kwargs):
        """Initialize the instance.

        Arguments:

          filename -- name of the resource file.
          src_file -- source file path.  This is an absolut filename of the source file.  The
            filename of the source file must not necessarily be the same as 'file'.  For examlpe a
            conversion may be involved (depending on particular 'Resource' subclass).
            
        """
        super(XResource, self).__init__(filename, **kwargs)
        self._src_file = src_file

    def src_file(self):
        return self._src_file
    
    def ok(self):
        return self._src_file is not None

    def get(self):
        if self._src_file is None:
            return None
        else:
            fh = open(self._src_file)
            data = fh.read()
            fh.close()
            return data
            
        
class XMedia(XResource, Media):
    pass
        
class XStylesheet(XResource, Stylesheet):
    pass
    
class XImage(XResource, Image):
    pass

class XScript(XResource, Script):
    pass

class XFlash(XResource, Flash):
    pass
    
class XTranscript(XResource):
    """A textual transcript of a recording ."""
    SUBDIR = 'transcripts'

    def __init__(self, filename, src_file=None, text=None, input_encoding='utf-8', **kwargs):
        """Arguments:
        
          text -- if defined and the source file does not exist, the
            destination file will be created using the specified text as its
            content.

        """
        super(XTranscript, self).__init__(filename, src_file=None, **kwargs)
        if text is None and src_file is not None:
            fh = codecs.open(src_file, encoding=input_encoding)
            try:
                text = ''.join(fh.readlines())
            except UnicodeDecodeError, e:
                raise Exception("Error while reading file %s: %s" % (self._src_file, e))
            fh.close()
        if text is not None:
            parts = [textwrap.fill(x) for x in text.replace("\r\n", "\n").split("\n\n")]
            text = unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE') + \
                   "\n\n".join(parts).replace('\n', '\r\n')
        self._text = text

    def ok(self):
        return self._text is not None
            
    def get(self):
        return self._text


###################################################################################################
###                                   Resource Providers                                       ####
###################################################################################################

    
class ResourceProvider(object):
    """An abstract base class for different resource provider implementations.

    The public methods defined here form the mandatory resource provider interface.
    
    """
    def resource(self, cls, filename, fallback=True, node=None, **kwargs):
        """Get the resource instance by its type and relative filename.

        Arguments:
        
          cls -- resource class.
          
          filename -- filename of the resource passed to the constructor.
            
          fallback -- if True, a valid 'Resource' instance will be returned even if the resource
            file doesn't exist.  The problem will be logged, but the program will continue as if
            the resource was there.  If False, None is returned when the resource file doesn't
            exist.

          node -- The node, for which the resource is allocated.  This can be either the
            'ContentNode' instance or a node identifier as a string (passing a string may be useful
            in content construction time, when the node instance is not created yet).  When None,
            the resource is considered to be global.  Global resources belong to all nodes and thus
            are returned for any 'node' argument when querying the 'resources()' method.
          
          kwargs -- resource specific constructor arguments.

        The resource instances may be cached by their constructor arguments.  These cached
        instances may be shared for multiple nodes, but the provider is responsible for keeping
        track of their dependency on particular nodes (to be able to serve the 'resources()'
        queries correctly).

        """
        return None
    
    def resources(self, cls=None, node=None):
        """Return the list of all resources matching the query.

        Query arguments:

          cls -- Only return the resources of given class.
          
          node -- only return the resources which were allocated for given node ('ContentNode'
            instance) or which are global (were allocated without passing the 'node' argument to
            the 'resource()' method.  If None, all resources are returned without respect to the
            nodes to which they belong.
        
        """
        return ()
        

class StaticResourceProvider(object):
    """Provides resources from a static list passed to the constructor.

    This resource provider is practical when the list of resources is already known in the
    construction time.  It may be for example read from a database etc.
    
    """

    def __init__(self, resources, **kwargs):
        self._resources = resources
        self._dict = None
        super(StaticResourceProvider, self).__init__(**kwargs)

    def resource(self, cls, filename, fallback=False, node=None, **kwargs):
        if self._dict is None:
            self._dict = dict([(r.filename(), r) for r in self._resources])
        resource = self._dict.get(filename)
        if not isinstance(resource, cls):
            resource = None
        if resource is None and fallback:
            resource = cls(filename, **kwargs)
        return resource

    def resources(self, cls=None, node=None):
        if cls is not None:
            return [r for r in self._resources if isinstance(r, cls)]
        else:
            return self._resources
        

class FileResourceProvider(ResourceProvider):
    """Automatically locates source files of the allocated resources.
    
    The possible source directories are first searched for the source file:

      * the directory passed as the 'searchdir' argument to the 'resource()' method call,
      * all directories passed as the 'dirs' argument to the provider constructor,
      * default resource directory ('config.default_resource_dir').

    """
    _CONVERSIONS = {'mp3': ('wav',),
                    'ogg': ('wav',)}
    """A dictionary of alternative source filename extensions.  When the input file is not found,
    given alternative filename extensions are also tried.  The exporter is then responsible for the
    conversion."""
    
    def __init__(self, dirs, **kwargs):
        assert isinstance(dirs, (list, tuple))
        self._dirs = tuple(dirs)
        self._cache = {}
        super(FileResourceProvider, self).__init__(**kwargs)
        
    def _resource(self, cls, filename, fallback=True, searchdir=None, **kwargs):
        if not issubclass(cls, XResource):
            assert issubclass(cls, Resource), cls
            return fallback and cls(*args, **kwargs) or None
        dirs = [os.path.join(dir, cls.SUBDIR) for dir in
                self._dirs + (config.default_resource_dir,)]
        if searchdir is not None:
            dirs.insert(0, searchdir)
        basename, ext = os.path.splitext(filename)
        altnames = [basename +'.'+ e
                    for e in self._CONVERSIONS.get(ext.lower()[1:], ()) if e != ext]
        for d in dirs:
            for src_file in [filename] + altnames:
                src_path = os.path.join(d, src_file)
                if os.path.exists(src_path):
                    return cls(filename, src_file=src_path, **kwargs)
                elif src_path.find('*') != -1:
                    pathlist = glob.glob(src_path)
                    if pathlist:
                        pathlist.sort()
                        return [cls(os.path.splitext(path[len(d)+1:])[0]+ext, src_file=path,
                                    **kwargs)
                                for path in pathlist]
        if fallback:
            result = cls(filename, src_file=None, **kwargs)
            if not result.ok():
                log("Resource file not found:", filename, dirs)
        else:
            result = None
        return result

    def resource(self, cls, filename, fallback=True, node=None, searchdir=None, **kwargs):
        key = (cls, filename, tuple(kwargs.items()))
        try:
            resource, nodes = self._cache[key]
        except KeyError:
            resource = self._resource(cls, filename, fallback=fallback, searchdir=searchdir,
                                      **kwargs)
            nodes = []
            self._cache[key] = (resource, nodes)
        if isinstance(node, ContentNode):
            node_id = node.id()
        else:
            node_id = node
        if node_id not in nodes:
            nodes.append(node_id) 
        return resource

    def resources(self, cls=None, node=None):
        if cls is None:
            cls = Resource
        result = []
        for resource, nodes in self._cache.values():
            if node is None or node.id() in nodes or None in nodes:
                if isinstance(resource, (list, tuple)):
                    for r in resource:
                        if isinstance(r, cls):
                            result.append(r)
                elif isinstance(resource, cls):
                    result.append(resource)
        return result
    
