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

from course import ContentNode
from util import *

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
            src_dirs = [os.path.join(d, self.SUBDIR)
                        for d in (self._parent.root_node().src_dir(),
                                  self._parent.default_resource_dir())]
            dst_subdir = self.SUBDIR
        else:
            src_dirs = (os.path.join(parent.src_dir(), self.SUBDIR), )
            dst_subdir = os.path.join(self.SUBDIR, parent.subdir())
        self._src_path = self._find_source_file(src_dirs, file)
        self._dst_path = os.path.join(dst_subdir, file)
        self._check_file()

    def _check_file(self):
        assert os.path.exists(self._src_path), \
               "Resource file '%s' doesn't exist!" % self._src_path
        
    def _find_source_file(self, dirs, file):
        for d in dirs:
            path = os.path.join(d, file)
            if os.path.exists(path):
                return path
        return os.path.join(dirs[0], file)
                
    def _destination_file(self, dir):
        return os.path.join(dir, self._dst_path)

    def url(self):
        return '/'.join(self._dst_path.split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

    def export(self, dir):
        dst_path = self._destination_file(dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(self._src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(self._src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            self._export(dir)
            
    def _export(self, dir):
        shutil.copy(self._src_path, self._destination_file(dir))
        print "%s: file copied." % self._destination_file(dir)


class Media(Resource):
    """Representation of a media object used within the content."""
    SUBDIR = 'media'
    
    def __init__(self, parent, file, shared=False, tts_input=None):
        """Initialize the instance.

        Arguments:

          parent, file, shared -- See 'Resource.__init__()'.
          tts_input -- if defined and the source file does not exist, the
            destination file will be generated via TTS.  The given string will
            be synthesized.

        """
        ext = os.path.splitext(file)[1]
        assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" %ext
        self._tts_input = tts_input   
        super(Media, self).__init__(parent, file, shared=shared)
        
    def _check_file(self):
        if self._tts_input is None:
            super(Media, self)._check_file()
        
    def _find_source_file(self, dirs, file):
        basename, extension = os.path.splitext(file)
        dirs += (os.path.join(self._parent.src_dir(), Transcript.SUBDIR),)
        for ext in ('.ogg','.mp3','.wav','.tts.txt', '.txt'):
            path = super(Media, self)._find_source_file(dirs, basename + ext)
            if os.path.exists(path):
                return path
        return super(Media, self)._find_source_file(dirs, file)

    def _command(self, which, errmsg):
        var = 'LCG_%s_COMMAND' % which
        try:
            return os.environ[var]
        except KeyError:
            raise "Environment variable %s not set!\n" % var + errmsg

    def _open_stream_from_tts(self):
        if self._tts_input is not None:
            text = self._tts_input
        else:
            fh = codecs.open(self._src_path,
                             encoding=self._parent.input_encoding())
            text = ''.join(fh.readlines())
            fh.close()
        cmd = self._command('TTS', "Specify a TTS command synthesizing " + \
                            "the text on STDIN to a wave on STDOUT.")
        print "  - generating with TTS: %s" % cmd
        input, output = os.popen2(cmd, 'b')
        input.write(text.encode(self._parent.input_encoding()))
        input.close()
        return output
    
    def _open_stream_from_encoder(self, output_format, wave):
        # The tmp file is a hack.  It would be better to send the data into a
        # pipe, but popen2 gets stuck while reading it.  Why?
        tmp = os.tmpnam() + '.wav'
        self._tmp_files.append(tmp)
        f = open(tmp, 'wb')
        copy_stream(wave, f)
        f.close()
        cmd = self._command(output_format, "Specify a command encoding a " + \
                            "wave on STDIN to %s on STDOUT." % output_format)
        print "  - converting to %s: %s" % (output_format, cmd)
        output = os.popen('cat %s |' % tmp + cmd)
        #input, output = os.popen2(convert_cmd)
        #copy_stream(wave, input)
        #input.close()
        return output

    
    def _export(self, dir):
        # Either create the file with tts or copy from source directory.
        input_format = os.path.splitext(self._src_path)[1].upper()[1:]
        output_format = os.path.splitext(self._dst_path)[1].upper()[1:]
        if input_format == output_format and os.path.exists(self._src_path):
            return super(Media, self)._export(dir)
        dst_path = self._destination_file(dir)
        wave = None
        data = None
        self._tmp_files = []
        try:
            print dst_path + ':'
            # Open the input stream
            if input_format == 'WAV' and os.path.exists(self._src_path):
                wave = open(self._src_path)
            elif input_format in ('TXT', 'TTS.TXT') or \
                     self._tts_input is not None:
                wave = self._open_stream_from_tts() 
            else:
                raise "Unknown input format: %s" % input_format
            if output_format == 'WAV':
                data = wave
            else:
                data = self._open_stream_from_encoder(output_format, wave)
            # Write the output stream
            output_file = open(dst_path, 'wb')
            copy_stream(data, output_file)
            output_file.close()
        finally:
            if wave is not None:
                wave.close()                
            if data is not None:
                data.close()
            # This is just because of the hack in _open_output_stream().
            for f in self._tmp_files:
                os.remove(f)
        
        
class Script(Resource):
    """Representation of a script object used within the content."""
    SUBDIR = 'scripts'

    
class Stylesheet(Resource):
    """Representation of a stylesheet used within the content."""
    SUBDIR = 'css'

    
class Transcript(Resource):
    """Representation of a textual recording transcript."""
    SUBDIR = 'transcripts'
    
    def __init__(self, parent, file, shared=False):
        super(Transcript, self).__init__(parent, file, shared=shared)

