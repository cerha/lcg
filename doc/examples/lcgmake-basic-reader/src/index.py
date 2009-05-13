# -*- coding: utf-8 -*-
import lcg

class Reader(lcg.DocFileReader):
    """This is a very simple reader which reads in one file and
    processes it.  This reader doesn't do anything special. You could
    however override its methods to make LCG behave the way you like.

    This example is useful as a template if you want to create your
    own Reader.  If you want to just compile one text file, you should
    simply use:

            lcgmake file.txt
    """

    def __init__(self, *args, **kwargs):
        """Initialize the instance.        
        """
        super(Reader, self).__init__(id='src1', **kwargs)


    # Here you would override the DocFileReader methods


