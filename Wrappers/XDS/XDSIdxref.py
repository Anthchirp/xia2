#!/usr/bin/env python
# XDSIdxref.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=IDXREF module in XDS.
#

import os
import sys
import math
import shutil

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from XDS import header_to_xds, xds_check_version_supported, xds_check_error
from XDS import XDSException
from Handlers.Streams import Debug

# specific helper stuff
from XDSIdxrefHelpers import _parse_idxref_lp, _parse_idxref_lp_distance_etc, \
     _parse_idxref_lp_subtree

from Experts.LatticeExpert import SortLattices

# global flags 
from Handlers.Flags import Flags

# helpful expertise from elsewhere
from Experts.SymmetryExpert import lattice_to_spacegroup_number

def XDSIdxref(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIdxrefWrapper(DriverInstance.__class__,
                           FrameProcessor):
        '''A wrapper for wrapping XDS in idxref mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...
            
            
            self._parallel = Flags.get_parallel()

            if self._parallel <= 1:
                self.set_executable('xds')
            else:
                self.set_executable('xds_par')

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = []
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            self._org = [0.0, 0.0]

            self._starting_angle = 0.0
            self._starting_frame = 0

            self._cell = None
            self._symm = 0

            # options
            self._reversephi = False

            # results

            self._refined_beam = (0, 0)
            self._refined_distance = 0

            self._indexing_solutions = { }

            self._indxr_input_lattice = None
            self._indxr_input_cell = None
            
            self._indxr_lattice = None
            self._indxr_cell = None
            self._indxr_mosaic = None

            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = ['SPOT.XDS']

            self._output_data_files_list = ['SPOT.XDS',
                                            'XPARM.XDS']

            self._index_tree_problem = False

            return

        # getter and setter for input / output data

        def set_starting_frame(self, starting_frame):
            self._starting_frame = starting_frame

        def set_starting_angle(self, starting_angle):
            self._starting_angle = starting_angle

        def set_indexer_input_lattice(self, lattice):
            self._indxr_input_lattice = lattice
            return

        def set_indexer_user_input_lattice(self, user):
            self._indxr_user_input_lattice = user
            return

        def set_indexer_input_cell(self, cell):
            if not type(cell) == type(()):
                raise RuntimeError, 'cell must be a 6-tuple de floats'

            if len(cell) != 6:
                raise RuntimeError, 'cell must be a 6-tuple de floats'

            self._indxr_input_cell = tuple(map(float, cell))
            return

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data
            return

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def get_refined_beam(self):
            return self._refined_beam

        def get_refined_distance(self):
            return self._refined_distance

        def get_indexing_solutions(self):
            return self._indexing_solutions

        def get_indexing_solution(self):
            return self._indxr_lattice, self._indxr_cell, self._indxr_mosaic

        def set_reversephi(self, reversephi = True):
            self._reversephi = reversephi
            return

        def get_index_tree_problem(self):
            return self._index_tree_problem

        # this needs setting up from setup_from_image in FrameProcessor

        def set_beam_centre(self, x, y):
            self._org = float(x), float(y)

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def add_spot_range(self, start, end):
            self._spot_range.append((start, end))

        def set_background_range(self, start, end):
            self._background_range = (start, end)

        def run(self, ignore_errors = False):
            '''Run idxref.'''

            image_header = self.get_header()

            # crank through the header dictionary and replace incorrect
            # information with updated values through the indexer
            # interface if available...

            # need to add distance, wavelength - that should be enough...

            if self.get_distance():
                image_header['distance'] = self.get_distance()

            if self.get_wavelength():
                image_header['wavelength'] = self.get_wavelength()

            header = header_to_xds(image_header, reversephi = self._reversephi)

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=IDXREF\n')
            xds_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                          self._parallel) 
            
            # FIXME this needs to be calculated from the beam centre...
            
            xds_inp.write('ORGX=%f ORGY=%f\n' % \
                          tuple(self._org))

            if self._starting_frame and self._starting_angle:
                xds_inp.write('STARTING_FRAME=%d\n' % \
                              self._starting_frame)
                xds_inp.write('STARTING_ANGLE=%f\n' % \
                              self._starting_angle)

            # FIXME this looks like a potential bug - what will
            # happen if the input lattice has not been set??
            if self._indxr_input_cell:
                self._cell = self._indxr_input_cell
            if self._indxr_input_lattice:
                self._symm = lattice_to_spacegroup_number(
                    self._indxr_input_lattice)

            if self._cell:
                xds_inp.write('SPACE_GROUP_NUMBER=%d\n' % self._symm)
                cell_format = '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f'
                xds_inp.write('UNIT_CELL_CONSTANTS=%s\n' % \
                              cell_format % self._cell)

            for record in header:
                xds_inp.write('%s\n' % record)

            name_template = os.path.join(self.get_directory(),
                                         self.get_template().replace('#', '?'))

            record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
                     name_template

            xds_inp.write(record)

            xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)
            for spot_range in self._spot_range:
                xds_inp.write('SPOT_RANGE=%d %d\n' % spot_range)
            xds_inp.write('BACKGROUND_RANGE=%d %d\n' % \
                          self._background_range)

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'XDS.INP'),
                            os.path.join(self.get_working_directory(),
                                         '%d_IDXREF.INP' % self.get_xpid()))

            # write the input data files...

            for file in self._input_data_files_list:
                open(os.path.join(
                    self.get_working_directory(), file), 'wb').write(
                    self._input_data_files[file])

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())
            if not ignore_errors:
                xds_check_error(self.get_all_output())

            # copy the LP file
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'IDXREF.LP'),
                            os.path.join(self.get_working_directory(),
                                         '%d_IDXREF.LP' % self.get_xpid()))

            # parse the output

            lp = open(os.path.join(
                self.get_working_directory(), 'IDXREF.LP'), 'r').readlines()

            self._idxref_data = _parse_idxref_lp(lp)

            st = _parse_idxref_lp_subtree(lp)

            if 2 in st:
            
                if st[2] > st[1] / 10:
                    Debug.write('Look closely at autoindexing solution!')
                    self._index_tree_problem = True
                    for j in sorted(st):
                        Debug.write('%2d: %5d' % (j, st[j]))

            for j in range(1, 45):
                if not self._idxref_data.has_key(j):
                    continue
                data = self._idxref_data[j]
                lattice = data['lattice']
                fit = data['fit']
                cell = data['cell']
                mosaic = data['mosaic']
                reidx = data['reidx']

                # only consider indexing solutions with goodness of fit < 40
                # or any value (< 200) if we have been provided the
                # input unit cell... but # 2731

                if fit < 40.0 or (self._cell and fit < 200.0):
                    # bug 2417 - if we have an input lattice then we
                    # don't want to include anything higher symmetry
                    # in the results table...

                    if self._symm:
                        if lattice_to_spacegroup_number(lattice) > self._symm:
                            Debug.write('Ignoring solution with lattice %s' % \
                                        lattice)
                            continue
                    
                    if self._indexing_solutions.has_key(lattice):
                        if self._indexing_solutions[lattice][
                            'goodness'] < fit:
                            continue
                        
                    self._indexing_solutions[lattice] = {
                        'goodness':fit,
                        'cell':cell}

            # get the highest symmetry "acceptable" solution
            
            list = [(k, self._indexing_solutions[k]['cell']) for k in \
                    self._indexing_solutions.keys()]

            # if there was a preassigned cell and symmetry return now
            # with everything done, else select the "top" solution and
            # reindex, resetting the input cell and symmetry.

            if self._cell:

                # select the solution which matches the input unit cell

                Debug.write(
                    'Target unit cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    self._cell)

                for l in list:
                    if lattice_to_spacegroup_number(l[0]) == self._symm:
                        # this should be the correct solution...
                        # check the unit cell...
                        cell = l[1]
                        cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % cell
                        Debug.write(
                            'Chosen unit cell: %s' % cell_str)

                        for j in range(6):
                            if math.fabs(cell[j] - self._cell[j]) > 5 \
                                   and False:
                                raise RuntimeError, \
                                      'bad unit cell [%d] in idxref' % j

                        Debug.write('Removed the check in here...')

                        self._indxr_lattice = l[0]
                        self._indxr_cell = l[1]
                        self._indxr_mosaic = mosaic

                        # return True
            
            else:

                # select the top solution as the input cell and reset the
                # "indexing done" flag
                    
                sorted_list = SortLattices(list)

                self._symm = lattice_to_spacegroup_number(sorted_list[0][0])
                self._cell = sorted_list[0][1]

                return False
            
            # get the refined distance &c.

            beam, distance = _parse_idxref_lp_distance_etc(lp)

            self._refined_beam = beam
            self._refined_distance = distance
            
            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = open(os.path.join(
                    self.get_working_directory(), file), 'rb').read()

            return True

    return XDSIdxrefWrapper()

if __name__ == '__main__':

    idxref = XDSIdxref()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    
    idxref.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # FIXED 12/DEC/06 need to work out how this is related to the beam centre
    # from labelit...
    
    for file in ['SPOT.XDS']:
        idxref.set_input_data_file(file, open(file, 'rb').read())

    idxref.set_beam_centre(1030, 1066)

    idxref.set_data_range(1, 1)
    idxref.set_background_range(1, 1)
    idxref.add_spot_range(1, 1)
    idxref.add_spot_range(90, 90)

    idxref.run()


