#!/usr/bin/env python
# MultiCrystalAnalysis.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# wrapper for xia2 MultiCrystalAnalysis module

from __future__ import division
import os

def MultiCrystalAnalysis(DriverType = None):
  '''A factory for MultiCrystalAnalysisWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class MultiCrystalAnalysisWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('cctbx.python')
      self._argv = []
      self._nproc = None
      self._njob = None
      self._mp_mode = None
      self._phil_file = None
      return

    def add_command_line_args(self, args):
      self._argv.extend(args)

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running MultiCrystalAnalysis.py')

      self.clear_command_line()

      from Modules import MultiCrystalAnalysis as mca_module
      self.add_command_line(mca_module.__file__)

      for arg in self._argv:
        self.add_command_line(arg)
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return MultiCrystalAnalysisWrapper()

