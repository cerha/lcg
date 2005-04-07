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

from lcg import *

class ResourceNotFound(Exception):
    def __init__(self, filename):
        msg = "Resource file not found: %s" % filename
        Exception.__init__(self, msg)
    
    
class Resource(object):
    """Base resource class.
    
    Instances should not be constructed directly.  Use the
    'ContentNode.resource()' method instead.

    """
    SUBDIR = 'resources'
    
    def __init__(self, parent, file, shared=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this resource belongs to.
          file -- path to the actual resource file relative to its parent
            node's source/destination directory.
          shared -- a boolean flag indicating that the file may be shared by
            multiple nodes (is not located within the node-specific
            subdirectory, but rather in a course-wide resource directory).

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._file = file
        self._shared = shared
        if shared:
            src_dirs = [''] + [os.path.join(d, self.SUBDIR)
                               for d in (self._parent.root_node().src_dir(),
                                         config.default_resource_dir)]
            dst_subdir = self.SUBDIR
        else:
            src_dirs = (os.path.join(parent.src_dir(), self.SUBDIR), )
            dst_subdir = os.path.join(self.SUBDIR, parent.subdir())
        self._src_path = self._find_source_file(src_dirs, file)
        self._dst_path = os.path.join(dst_subdir, file)
        self._check_file()

    def _check_file(self):
        if not os.path.exists(self._src_path):
            raise ResourceNotFound(self._src_path)
        
    def _find_source_file(self, dirs, file):
        for d in dirs:
            path = os.path.join(d, file)
            if os.path.exists(path):
                return path
        return os.path.join(dirs[0], file)
                
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
        shutil.copy(infile, outfile)
        print "%s: file copied." % outfile

    def get(self):
        fh = open(self._src_path)
        data = fh.read()
        fh.close()
        return data
            

        
class Media(Resource):
    """Representation of a media object used within the content."""
    SUBDIR = 'media'

    def __init__(self, parent, file, shared=False):
        basename, ext = os.path.splitext(file)
        assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" % ext
        super(Media, self).__init__(parent, file, shared=shared)
        
    def _find_source_file(self, dirs, file):
        basename, extension = os.path.splitext(file)
        for ext in ('.ogg','.mp3','.wav'):
            path = super(Media, self)._find_source_file(dirs, basename + ext)
            if os.path.exists(path):
                return path
        return super(Media, self)._find_source_file(dirs, file)

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
        print "%s: converting to %s: %s" % (outfile, output_format, cmd)
        command = cmd.replace('%infile', infile).replace('%outfile', outfile)
        if os.system(command):
            raise IOError("Subprocess returned a non-zero exit status.")
        
        
class Script(Resource):
    """Representation of a script object used within the content."""
    SUBDIR = 'scripts'

    
class Stylesheet(Resource):
    """Representation of a stylesheet used within the content."""
    SUBDIR = 'css'

    
class Transcript(Resource):
    """Representation of a textual recording transcript."""
    SUBDIR = 'transcripts'

    def __init__(self, parent, file, text=None, shared=False):
        """Initialize the instance.

        Arguments:

          parent, file, shared -- See 'Resource.__init__()'.
          text -- if defined and the source file does not exist, the
            destination file will be created using the specified text As its
            content.

        """
        self._text = text
        super(Transcript, self).__init__(parent, file, shared=shared)
    

    def _check_file(self):
        if self._text is None:
            super(Transcript, self)._check_file()
            
    def _additional_export_condition(self):
        return self._text is not None

    def _export(self, infile, outfile):
        if self._text is not None:
            text = self._text
        else:
            fh = codecs.open(infile, encoding=self._parent.input_encoding())
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
