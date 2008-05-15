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
abstract representation.  The resources are managed by the 'ResourceProvider' (see below).
    
"""

import os
import glob
import config

from lcg import *


class Resource(object):
    """Generic resource class."""
    
    SUBDIR = None
    """Name of the subdirectory where files are searched on input and stored on output."""
    
    def __init__(self, filename, title=None, descr=None, uri=None, relative_uri=False):
        super(Resource, self).__init__()
        assert isinstance(filename, (str, unicode)), filename
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert uri is None or isinstance(uri, (str, unicode)), uri
        self._filename = filename
        self._title = title
        self._descr = descr
        self._uri = uri
        self._relative_uri = relative_uri
                 
    def filename(self):
        return self._filename
        
    def title(self):
        return self._title
            
    def descr(self):
        return self._descr
        
    def uri(self):
        return self._uri

    def relative_uri(self):
        return self._relative_uri


class Image(Resource):
    """An image resource."""
    SUBDIR = 'images'

    def __init__(self, filename, size=None, **kwargs):
        super(Image, self).__init__(filename, **kwargs)
        self._size = size

    def size(self):
        return self._size


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
    recommended to create the instances directly.  The resource provider will supply the 'src_file'
    constructor argument to the resource constructor automatically.

    When an 'XResource' instance is found in node's dependencies, the exporter is than able to
    export the resource to the output since the input file is known.

    """
    
    def __init__(self, filename, src_file=None, **kwargs):
        """Initialize the instance.

        Arguments:

          filename -- name of the resource file.
          
          src_file -- absolut pathname of the source file.  The filename (last part of the path)
            must not necessarily be the same as 'filename'.  This may indicate that a conversion is
            necessary on export (see the particular 'Exporter' class for the supported
            conversions).  This argument may also be None to indicate, that the source file does
            not exist.  This may happen when the Resource instance is required by the application,
            but the source file was not found (so it will not be exported).
            
        """
        super(XResource, self).__init__(filename, **kwargs)
        self._src_file = src_file

    def src_file(self):
        """Return the absolute pathname of the source file as passed to the constructor."""
        return self._src_file
    
    def get(self):
        """Return the resource file contents as a byte string or None if it does not exist."""
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

    #def size(self):
    #    if self._size is None:
    #        import Image as Img
    #        img = Img.open(self._src_file)
    #        self._size = img.size
    #    return self._size

class XScript(XResource, Script):
    pass

class XFlash(XResource, Flash):
    pass


###################################################################################################
###                                   Resource Provider                                        ####
###################################################################################################

class ResourceProvider(object):
    """Resource provider.

    The resource provider may be used to allocate resources during content construction, as well as
    in export time.  The resource provider is designed to be shared among multilpe content nodes
    while still keeping track of the dependencies of each node on its resources.

    The source files for XResource subclasses are located automatically.  The possible source
    directories are searched for the source file in this order:
    
      * the directory passed as the 'searchdir' argument to the 'resource()' method call,
      * all directories passed as the 'dirs' argument to the provider constructor,
      * default resource directory ('config.default_resource_dir').

    """
    _CONVERSIONS = {'mp3': ('wav',),
                    'ogg': ('wav',)}
    """A dictionary of alternative source filename extensions.  When the input file is not found,
    given alternative filename extensions are also tried.  The exporter is then responsible for the
    conversion."""
    
    def __init__(self, dirs=(), resources=(), **kwargs):
        """Arguments:

          dirs -- sequence of directory names to search for resource input files (see the
            documentation of this class for more information).
          resources -- list of statically allocated resources already known in the construction
            time.

        """
        assert isinstance(dirs, (list, tuple)), dirs
        assert isinstance(resources, (list, tuple)), resources
        self._dirs = tuple(dirs)
        self._cache = {}
        super(ResourceProvider, self).__init__(**kwargs)
        
    def _resource(self, cls, filename, searchdir, fallback, warn, **kwargs):
        if issubclass(cls, XResource):
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
                            i = len(d)+1
                            return [cls(os.path.splitext(path[i:])[0]+ext, src_file=path, **kwargs)
                                    for path in pathlist]
            if warn:
                log("Resource file not found:", filename, dirs)
        else:
            assert issubclass(cls, Resource), cls
        if fallback:
            result = cls(filename, **kwargs)
        else:
            result = None
        return result

    def resource(self, cls, filename, node=None, searchdir=None, fallback=True, warn=True,
                 **kwargs):
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
        key = (cls, filename, tuple(kwargs.items()))
        try:
            resource, nodes = self._cache[key]
        except KeyError:
            resource = self._resource(cls, filename, searchdir, fallback, warn, **kwargs)
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
        """Return the list of all resources matching the query.

        Query arguments:

          cls -- Only return the resources of given class.
          
          node -- only return the resources which were allocated for given node ('ContentNode'
            instance) or which are global (were allocated without passing the 'node' argument to
            the 'resource()' method.  If None, all resources are returned without respect to the
            nodes to which they belong.
        
        """
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
    
class DummyResourceProvider(ResourceProvider):
    """Pretends all resources can be found without checking for the source files.
    
    The resource instance is always returned as if the file was actually found.

    This provider may be useful in the on-line web server environment, when the document is
    processed in one request and the resources are served in independent requests, so checking for
    files in the document serving request is only wasting system resources.
    
    """
    def _resource(self, cls, filename, *args, **kwargs):
        return cls(filename, **kwargs)
