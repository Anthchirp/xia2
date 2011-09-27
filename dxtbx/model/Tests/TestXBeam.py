#!/usr/bin/env python
# TestXBeam.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Tests for the XBeam class.

import math
import os
import sys

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from dxtbx.model.XBeam import XBeam
from dxtbx.model.XBeam import XBeamFactory

def TestXBeam():
    '''A test class for the XBeam class.'''

    cbf = XBeamFactory.imgCIF('phi_scan_001.cbf')

    print cbf

if __name__ == '__main__':

    TestXBeam()

