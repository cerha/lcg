#! /usr/bin/python2.3
# -*- coding: Latin-1 -*-

def my_visiblename(name):
    """Decide whether to show documentation on a variable."""
    # Certain special names are redundant.
    if name in ['__builtins__', '__doc__', '__file__', '__path__',
                '__module__', '__name__', '__weakref__', '__dict__']: return 0
    # Private names are hidden, but special names are displayed.
    if name.startswith('__') and name.endswith('__'): return 1
    return not name.startswith('_')


import inspect
#inspect.getmro = lambda object: []

import pydoc
pydoc.visiblename = my_visiblename

pydoc.cli()

