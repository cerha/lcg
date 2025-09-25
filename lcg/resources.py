# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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

The LCG content elements may depend on several external resources.  These
resources usually refer to external files, but in general, thay don't depend on
these files, they just provide their abstract representation.  The resources
are managed by the 'ResourceProvider' (see below).

"""
from __future__ import unicode_literals

import os
import glob
import sys
import lcg
import functools

_ = lcg.TranslatableTextFactory('lcg')

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class Resource(object):
    """Generic resource representation.

    Specific classes for certain resource types may be derived from this class.

    """

    SUBDIR = None
    """Name of the subdirectory where files are searched on input and stored on output."""
    EXTENSIONS = ()
    """All valid filename extensions for particular resource type."""
    _type_map = None

    @classmethod
    def subclass(cls, filename):
        """Return the Resource subclass matching given filename (by extension)."""
        def all_subclasses(c):
            subclasses = c.__subclasses__()
            return subclasses + [x for s in c.__subclasses__() for x in all_subclasses(s)]
        if cls._type_map is None:
            cls._type_map = dict((ext, c) for c in all_subclasses(cls) for ext in c.EXTENSIONS)
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        return cls._type_map.get(ext, Resource)

    def __init__(self, filename, title=None, descr=None, uri=None,
                 src_file=None, content=None, info=None):
        """Arguments:

          filename -- unique string identifying the resource (typisally its
            file name).
          title -- optional user visible resource title as a string or None.
          descr -- optional user visible resource description as a string or
            None.
          uri -- resource's URI as a string.  If None, the URI will be supplied
            by the exporter automatically (the exporter is normally responsible
            for exporting the file to a location with a corresponding URI).
            Supplying the URI directly to the resource constructor may be,
            however, needed when the resource is handled by the application
            specifically.
          src_file -- absolute pathname of the source file.  If not None, the
            resource data will be read from the file when needed (typicaly on
            export).  If None, the 'content' argument may provide the data from
            other source.  This argument is normally supplied by the
            'ResourceProvider', so you would typically not need to pass it
            manually.  The filename (last part of the path) must not
            necessarily be the same as 'filename'.  In some cases, however, a
            different filename suffix may indicate that a conversion is
            necessary on export (such as WAV to MP3).  The particular
            'Exporter' class is responsible for handling such conversions when
            necessary.
          content -- resource data as a bytes instance or a file-like object.
            Typically used when passing 'Resource' instances from application
            code.  Textual content (such as scripts, stylesheets, etc.) should
            be encoded in UTF-8.  Resources with 'content' are not located by
            the 'ResourceProvider' and may not be bound to files on the file
            system.

          info -- additional application specific
            information about the attachment.  No particular limitation on the
            content is defined and LCG ignores this value alltogether.

        """
        super(Resource, self).__init__()
        assert isinstance(filename, basestring), filename
        assert title is None or isinstance(title, basestring), title
        assert descr is None or isinstance(descr, basestring), descr
        assert uri is None or isinstance(uri, basestring), uri
        assert src_file is None or isinstance(src_file, basestring), src_file
        assert content is None or isinstance(content, bytes) or hasattr(content, 'read'), content
        self._filename = filename
        self._title = title
        self._descr = descr
        self._uri = uri
        self._src_file = src_file
        self._content = content
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

    def content(self):
        """Return the resource content as passed to the constructor or None."""
        return self._content

    def get(self):
        """Return the resource file data as a byte string or None.

        None is returned if this instance is not bound to any particular data
        (when neither 'src_file' nor 'content' was passed to its constructor).

        This method may only be called once, otherwise the behavior is undefined.

        """
        if self._src_file is not None:
            f = open(self._src_file, 'rb')
        elif isinstance(self._content, bytes):
            return self._content
        elif self._content:
            f = self._content
        else:
            return None
        with f:
            return f.read()


class Image(Resource):
    """An image of undefined type."""
    SUBDIR = 'images'
    EXTENSIONS = ('jpeg', 'jpg', 'gif', 'png', 'svg')

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
    EXTENSIONS = ('css',)

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
    """A JavaScript object used within the content."""
    SUBDIR = 'scripts'
    EXTENSIONS = ('js',)

    def __init__(self, filename, type=None, **kwargs):
        """Arguments:

        type -- script type analogous to HTML <script> tag type attribute.  Can
          contain a valid JavaScript MIME type or 'module' to indicate the
          script is actually a JavaScript module.  If None, defaults to
          'text/javascript'.

        """
        self._type = type
        super(Script, self).__init__(filename, **kwargs)

    def type(self):
        """Return the script type as passed to the constructor."""
        return self._type


class Translations(Resource):
    """Gettext translations .po file"""
    SUBDIR = 'translations'
    EXTENSIONS = ('po',)


class Media(Resource):
    """Media file, such as audio or video."""
    SUBDIR = 'media'


class Audio(Media):
    """Audio media file."""
    EXTENSIONS = ('mp3', 'wave', 'ogg', 'oga', 'wav', 'aac', 'm4a')


class Video(Media):
    """Video media file."""
    EXTENSIONS = ('ogv', 'mp4', 'webm', '3gp')


class Flash(Resource):
    """Adobe/Macromedia Flash object."""
    SUBDIR = 'flash'
    EXTENSIONS = ('swf',)


###################################################################################################
#                                     Resource Provider                                           #
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
    other way but LCG should still be able to locate them.

    Unsuccessful resource allocations are usually logged together with the
    exact list of directories where the file was searched so this might help
    you to discover problems in your setup.

    """

    class OrderedDict(object):
        # Totally simplistic - just what we need to get the resources in the order of allocation.
        # This is needed for the correct precedence of stylesheets.

        def __init__(self, pairs):
            self._dict = dict(pairs)
            self._values = [v for k, v in pairs]

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
        self._dirs = tuple(dirs) + (os.path.join(os.path.dirname(__file__), 'resources'),)
        self._cache = self.OrderedDict([(self._cache_key(r.filename(), {}), (r, [None]))
                                        for r in resources])
        super(ResourceProvider, self).__init__(**kwargs)

    def _cache_key(self, filename, kwargs):
        return (filename, tuple(kwargs.items()))

    def _resource(self, filename, searchdir, warn, **kwargs):
        dirs = self._dirs
        cls = Resource.subclass(filename)
        if kwargs.get('content') is not None:
            return cls(filename, **kwargs)
        if cls.SUBDIR:
            dirs = tuple(functools.reduce(
                lambda a, b: a + b, ((os.path.join(dir, cls.SUBDIR), dir) for dir in dirs), ()
            ))
        if searchdir is not None:
            dirs = (searchdir,) + dirs
        basename, ext = os.path.splitext(filename)
        for directory in dirs:
            src_path = os.path.join(directory, filename)
            if sys.version_info[0] == 2:
                src_path = src_path.encode('utf-8')
            if os.path.isfile(src_path):
                return cls(filename, src_file=src_path, **kwargs)
            elif src_path.find('*') != -1:
                pathlist = [path for path in glob.glob(src_path) if os.path.isfile(path)]
                if pathlist:
                    pathlist.sort()
                    i = len(directory) + 1
                    return [cls(os.path.splitext(path[i:])[0] + ext, src_file=path, **kwargs)
                            for path in pathlist]
        if warn:
            warn(_("Resource file not found: %(filename)s %(search_path)s",
                   filename=filename,
                   search_path=tuple(dirs)))
        return None

    def resource(self, filename, node=None, searchdir=None, warn=lcg.log, **kwargs):
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
        key = self._cache_key(filename, kwargs)
        try:
            resource, nodes = self._cache[key]
        except KeyError:
            resource = self._resource(filename, searchdir, warn, **kwargs)
            nodes = []
            self._cache[key] = (resource, nodes)
        if isinstance(node, lcg.ContentNode):
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
