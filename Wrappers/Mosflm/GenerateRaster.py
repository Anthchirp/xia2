#!/usr/bin/env python
# GenerateRaster.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Generate the raster parameters from spot finding to help Mosflm cell 
# refinement if other programs used for indexing (e.g. Labelit or DIALS)

def GenerateRaster(DriverType = None):
    '''A factory for GenerateRasterWrapper(ipmosflm) classes.'''

    from Driver.DriverFactory import DriverFactory
    DriverInstance = DriverFactory.Driver(DriverType)

    class GenerateRasterWrapper(DriverInstance.__class__):

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            from Handlers.Executables import Executables
            if Executables.get('ipmosflm'):
                self.set_executable(Executables.get('ipmosflm'))
            else:
                import os
                self.set_executable(os.path.join(
                    os.environ['CCP4'], 'bin', 'ipmosflm'))

            return

        def __call__(self, indxr, images):
            '''Get out the parameters from autoindexing without using the
            result - this is probably ok as it is quite quick ;o).'''

            from Handlers.Streams import Debug
            Debug.write('Running mosflm to generate RASTER, SEPARATION')

            self.start()
            self.input('template "%s"' % indxr.get_template())
            self.input('directory "%s"' % indxr.get_directory())
            self.input('beam %f %f' % indxr.get_indexer_beam())
            self.input('distance %f' % indxr.get_indexer_distance())
            self.input('wavelength %f' % indxr.get_wavelength())

            for i in images:
                self.input('findspots find %d' % i)

            self.input('go')

            self.close_wait()

            p = { }

            # scrape from the output the values we want...
            
            for o in self.get_all_output():
                if 'parameters have been set to' in o:
                    p['raster'] = map(int, o.split()[-5:])
                if '(currently SEPARATION' in o:
                    p['separation'] = map(float, o.replace(')', '').split()[-2:])

            return p
        
    return GenerateRasterWrapper()
