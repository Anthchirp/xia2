from __future__ import absolute_import, division, print_function

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Streams import Chatter, Debug


def DialsMerge(DriverType=None):
    """A factory for DialsMergeWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsMergeWrapper(DriverInstance.__class__):
        """A wrapper for dials.merge"""

        def __init__(self):
            # generic things
            super(DialsMergeWrapper, self).__init__()

            self.set_executable("dials.merge")

            # clear all the header junk
            self.reset()

            self._experiments_filename = None
            self._reflections_filename = None
            self._mtz_filename = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def get_reflections_filename(self):
            return self._reflections_filename

        def set_mtz_filename(self, filename):
            self._mtz_filename = filename

        def get_mtz_filename(self):
            return self._mtz_filename

        def run(self):
            """Run dials.merge"""
            self.clear_command_line()

            assert self._experiments_filename
            assert self._reflections_filename
            self.add_command_line(self._reflections_filename)
            self.add_command_line(self._experiments_filename)

            if self._mtz_filename:
                self.add_command_line("output.mtz=%s" % self._mtz_filename)

            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                Chatter.write(
                    "dials.merge failed, see log file for more details:\n  %s"
                    % self.get_log_file()
                )
                raise

            Debug.write("dials.merge status: OK")

    return DialsMergeWrapper()