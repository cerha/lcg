# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2009, 2011, 2012 Brailcom, o.p.s.
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

"""Representation and management of external resources.

The LCG content elements may depend on several external resources.  These resources usually refer
to external files, but in general, thay don't depend on these files, they just provide their
abstract representation.  The resources are managed by the 'ResourceProvider' (see below).
    
"""
import os
import glob

from lcg import *


class Resource(object):
    """Generic resource representation.

    Specific classes for certain resource types may be derived from this class.
    
    """
    
    SUBDIR = None
    """Name of the subdirectory where files are searched on input and stored on output."""
    
    def __init__(self, filename, title=None, descr=None, src_file=None, uri=None, info=None):
        """Arguments:
        
          filename -- unique string identifying the resource (typisally its
            file name).
          title -- optional user visible resource title as a string or None.
          descr -- optional user visible resource description as a string or None.
          src_file -- absolut pathname of the source file.  If None, the resource will not be
            exported.  The source file is normally located by the resource provider and this
            argument is supplied automatically, so you usually do not need to care about it.  In
            any case, the exporter is responsible for writing the resources which have the source
            file defined to the output (if necessary for given output format).  The filename (last
            part of the path) must not necessarily be the same as 'filename'.  This may indicate
            that a conversion is necessary on export (such as WAV to MP3; see the particular
            'Exporter' class for the supported conversions).
          uri -- resource's URI as a string.  If None, the URI will be supplied by the exporter
            automatically (the exporter is normally responsible for exporting the file to a
            location with a corresponding URI).  Supplying the URI directly to the resource
            constructor may be, however, needed when the resource is handled by the application
            specifically.
          info -- additional application specific information about the
            attachment.  No particular limitation on the content is defined and
            LCG ignores this value alltogether.
            
        """
        super(Resource, self).__init__()
        assert isinstance(filename, (str, unicode)), filename
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert src_file is None or isinstance(src_file, (str, unicode)), src_file
        assert uri is None or isinstance(uri, (str, unicode)), uri
        self._filename = filename
        self._title = title
        self._descr = descr
        self._src_file = src_file
        self._uri = uri
        self._info = info
                 
    def filename(self):
        """Return the unique resource identifier as a string."""
        return self._filename
        
    def title(self):
        """Return the resource title passed to the constructor or None."""
        return self._title
            
    def descr(self):
        """Return the resource description passed to the constructor or None."""
        return self._descr
        
    def src_file(self):
        """Return the absolute pathname of the source file as passed to the constructor."""
        return self._src_file
    
    def uri(self):
        """Return the resource URI passed to the constructor or None."""
        return self._uri

    def info(self):
        """Return the resource info as passed to the constructor or None."""
        return self._info

    def get(self):
        """Return the resource file contents as a byte string or None if it does not exist."""
        if self._src_file is None:
            return None
        else:
            fh = open(self._src_file)
            data = fh.read()
            fh.close()
            return data


class Image(Resource):
    """An image of undefined type."""
    SUBDIR = 'images'
    
    def __init__(self, filename, size=None, thumbnail=None, **kwargs):
        """Arguments:

        size -- explicit image size as a tuple of two integers (width, height)
          in pixels.  If not None, the HTML output will use these values when
          the 'Image' instance is used within an 'InlineImage' element.
          
        thumbnail -- image thumbnail an an Image instance.  If not None, the
          image will not be rendered in full size when used within an
          'InlineImage' element, but given thumbnail will be used instead.  The
          thumbnail will be clickable and will display the full size image only
          upon a user request.

        """
        self._size = size
        self._thumbnail = thumbnail
        super(Image, self).__init__(filename, **kwargs)

    def size(self):
        return self._size

    def thumbnail(self):
        return self._thumbnail

class Stylesheet(Resource):
    """A cascading style sheet."""
    SUBDIR = 'css'

    def __init__(self, filename, media='all', **kwargs):
        """Arguments:

        media -- a string determining the stylesheet media type as defined by
          CSS, such as 'all', 'screen', 'print', etc.

        """
        self._media = media
        super(Stylesheet, self).__init__(filename, **kwargs)

    def media(self):
        return self._media
    
class Script(Resource):
    """A java/ecma/... script object used within the content."""
    SUBDIR = 'scripts'

class Media(Resource):
    """Media file, such as audio or video."""
    SUBDIR = 'media'

class Audio(Media):
    """Audio media file of undefined type."""
    pass

class Video(Media):
    """Video media file of undefined type."""
    pass

class Flash(Resource):
    """Adobe/Macromedia Flash object."""
    SUBDIR = 'flash'
    

###################################################################################################
###                                   Resource Provider                                        ####
###################################################################################################

class ResourceProvider(object):
    """Resource provider.

    The resource provider may be used to allocate resources during content
    construction, as well as in export time.  The resource provider is designed
    to be shared among multilpe content nodes while still keeping track of the
    dependencies of each node on its resources.

    The resource files are searched in the source directories in this order:
    
      1) the directory passed as the 'searchdir' argument to the 'resource()'
         method call,

      2) type specific subdirectory of all directories passed as the 'dirs'
         argument to the provider constructor (see below for more info about
         type specific subdirectories)

      3) all directories passed as the 'dirs' argument to the provider
         constructor
      
      4) default resource directory set by 'config.default_resource_dir' (if
         not None).

    The type specific subdirectories mentioned in step 2) are given by the
    SUBDIR attribute defined by the corresponding resource type.  For example
    filename 'x.jpg' corresponds to the resource class Images, which defines
    SUBDIR = 'images', so the files are first searched in the subdirectory
    'images' within the source directories and only when not found in this type
    specific subdirectory, they are searched in the source directories directly
    in step 3).  This allows more flexibility in organization of the resource
    files.  Sometimes it is more practical to have different kinds of files
    arranged separately, sometimes it is more practical to group them in some
    other way but LCG shold still be able to locate them.

    Unsuccessful resource allocations are usually logged together with the
    exact list of directories where the file was searched so this might help
    you to discover problems in your setup.

    """
    _CONVERSIONS = {'mp3': ('wav',),
                    'ogg': ('wav',)}
    """A dictionary of alternative source filename extensions.  When the input file is not found,
    given alternative filename extensions are also tried.  The exporter is then responsible for the
    conversion."""
    
    _TYPEMAP = {'jpeg': Image,
                'jpg':  Image,
                'gif':  Image,
                'png':  Image,
                'mp3':  Audio,
                'ogg':  Audio,
                'css':  Stylesheet,
                'js':   Script,
                'swf':  Flash}
    
    class OrderedDict(object):
        # Totally simplistic - just what we need to get the resources in the order of allocation.
        # This is needed for the correct precedence of stylesheets.
        def __init__(self, pairs):
            self._dict = dict(pairs)
            self._values = [v for k,v in pairs]
        def __setitem__(self, key, value):
            self._values.append(value)
            self._dict[key] = value
        def __getitem__(self, key):
            return self._dict[key]
        def values(self):
            return self._values
    
    def __init__(self, resources=(), dirs=(), **kwargs):
        """Arguments:

          resources -- list of statically allocated resources already known in the construction
            time
          dirs -- sequence of directory names to search for resource input files (see the
            documentation of this class for more information)

        """
        assert isinstance(dirs, (list, tuple)), dirs
        assert isinstance(resources, (list, tuple)), resources
        self._dirs = tuple(dirs)
        if config.default_resource_dir is not None:
            self._dirs += (config.default_resource_dir,)
        self._cache = self.OrderedDict([(r.filename(), (r, [None])) for r in resources])
        super(ResourceProvider, self).__init__(**kwargs)
        
    def _resource(self, filename, searchdir, warn):
        dirs = list(self._dirs)
        try:
            ext = filename.rsplit('.', 1)[1]
            cls = self._TYPEMAP[ext.lower()]
        except (KeyError, IndexError):
            cls = Resource
        if cls.SUBDIR:
            dirs = [os.path.join(dir, cls.SUBDIR) for dir in self._dirs] + dirs
        if searchdir is not None:
            dirs.insert(0, searchdir)
        basename, ext = os.path.splitext(filename)
        altnames = [basename +'.'+ e
                    for e in self._CONVERSIONS.get(ext.lower()[1:], ()) if e != ext]
        for d in dirs:
            for src_file in [filename] + altnames:
                # Here we assume that the filesystem uses UTF-8 filenames.  If
                # it is not always the case, we may need to make it
                # configurable.
                src_path = unicode(os.path.join(d, src_file)).encode('utf-8')
                if os.path.isfile(src_path):
                    return cls(filename, src_file=src_path)
                elif src_path.find('*') != -1:
                    pathlist = [path for path in glob.glob(src_path) if os.path.isfile(path)]
                    if pathlist:
                        pathlist.sort()
                        i = len(d)+1
                        return [cls(os.path.splitext(path[i:])[0]+ext, src_file=path)
                                for path in pathlist]
        if warn:
            warn("Resource file not found: %s %s" % (filename, tuple(dirs)))
        return None

    def resource(self, filename, node=None, searchdir=None, warn=log):
        """Get the resource instance by its filename.

        Arguments:
        
          filename -- filename of the resource passed to the constructor.
            
          node -- The node, for which the resource is allocated.  This can be either the
            'ContentNode' instance or a node identifier as a string (passing a string may be useful
            in content construction time, when the node instance is not created yet).  When None,
            the resource is considered to be global.  Global resources belong to all nodes and thus
            are returned for any 'node' argument when querying the 'resources()' method.
          
        The resource instances may be cached by 'filename'.  These cached instances may be shared
        for multiple nodes, but the provider is responsible for keeping track of their dependency
        on particular nodes (to be able to serve the 'resources()' queries correctly).

        Unsuccessful resource allocations are usually logged together with the
        exact list of directories where the file was searched so this might help
        you to discover problems in your setup.

        """
        try:
            resource, nodes = self._cache[filename]
        except KeyError:
            resource = self._resource(filename, searchdir, warn)
            nodes = []
            self._cache[filename] = (resource, nodes)
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
                    result.extend([r for r in resource if isinstance(r, cls)])
                elif isinstance(resource, cls):
                    result.append(resource)
        return result

