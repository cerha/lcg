# -*- coding: utf-8 -*-
import lcg

class Reader(lcg.DocFileReader):

    def __init__(self, *args, **kwargs):
        """Initialize the instance.        
        """
        super(Reader, self).__init__(id='src1', **kwargs)


