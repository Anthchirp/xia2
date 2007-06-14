#!/usr/bin/env python
# Files.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A manager for files - this will record temporary and output files from 
# xia2, which can be used for composing a dump of "useful" files at the end
# if processing.
#
# This will also be responsible for migrating the data - that is, when
# the .xinfo file is parsed the directories referred to therein may be
# migrated to a local disk. This will use a directory created by
# tempfile.mkdtemp().

import os
import sys
import exceptions
import shutil
import tempfile
import time

from Environment import Environment
from Handlers.Streams import Chatter
from Handlers.Flags import Flags

class _FileHandler:
    '''A singleton class to manage files.'''

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

        self._log_files = { }
        self._log_file_keys = []

        # for putting the reflection files somewhere nice...
        self._data_files = []
        
        # for data migration to local disk, bug # 2274
        self._data_migrate = { }

    def migrate(self, directory):
        '''Migrate (or not) data to a local directory.'''

        if not Flags.get_migrate_data():
            # we will not migrate this data
            return directory

        if directory in self._data_migrate.keys():
            # we have already migrated this data
            return self._data_migrate[directory]

        # create a directory to move data to...
        self._data_migrate[directory] = tempfile.mkdtemp()

        # copy all files in source directory to new directory
        # retaining timestamps etc.

        start_time = time.time()

        migrated = 0
        migrated_dir = 0
        for f in os.listdir(directory):
            # copy over only files....
            if os.path.isfile(os.path.join(directory, f)):
                shutil.copy2(os.path.join(directory, f),
                             self._data_migrate[directory])
                migrated += 1
            elif os.path.isdir(os.path.join(directory, f)):
                shutil.copytree(os.path.join(directory, f),
                                os.path.join(self._data_migrate[directory],
                                             f))
                migrated_dir += 1
                

        Debug.write('Migrated %d files from %s to %s' % \
                    (migrated, directory, self._data_migrate[directory]))

        if migrated_dir > 0:
            Debug.write('Migrated %d directories from %s to %s' % \
                        (migrated_dir, directory,
                         self._data_migrate[directory]))

        end_time = time.time()
        duration = end_time - start_time
        
        Debug.write('Migration took %s' % \
                    time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

        return self._data_migrate[directory]
        
    def cleanup(self):
        out = open('xia-files.txt', 'w')
        for f in self._temporary_files:
            try:
                os.remove(f)
                out.write('Deleted: %s\n' % f)
            except exceptions.Exception, e:
                out.write('Failed to delete: %s (%s)\n' % \
                          (f, str(e)))

        for f in self._data_migrate.keys():
            d = self._data_migrate[f]
            shutil.rmtree(d)
            out.write('Removed directory %s' % d)
                
        for f in self._output_files:
            out.write('Output file (%s): %s\n' % f)

        # copy the log files
        log_directory = Environment.generate_directory('LogFiles')
        for f in self._log_file_keys:
            filename = os.path.join(log_directory,
                                    '%s.log' % f.replace(' ', '_'))
            shutil.copyfile(self._log_files[f],
                            filename)
            out.write('Copied log file %s to %s\n' % \
                      (self._log_files[f],
                       filename))

        # copy the data files
        data_directory = Environment.generate_directory('DataFiles')
        for f in self._data_files:
            filename = os.path.join(data_directory,
                                    os.path.split(f)[-1])
            shutil.copyfile(f, filename)
            out.write('Copied data file %s to %s\n' % \
                      (f, filename))

        out.close()
        return

    def record_output_file(self, filename, type):
        self._output_files.append((type, filename))
        return

    def record_log_file(self, tag, filename):
        '''Record a log file.'''
        self._log_files[tag] = filename
        if not tag in self._log_file_keys:
            self._log_file_keys.append(tag)

    def record_data_file(self, filename):
        '''Record a data file.'''
        if not filename in self._data_files:
            self._data_files.append(filename)
        return

    def record_temporary_file(self, filename):
        # allow for file overwrites etc.
        if not filename in self._temporary_files:
            self._temporary_files.append(filename)
        return

FileHandler = _FileHandler()

def cleanup():
    FileHandler.cleanup()

if __name__ == '__main__':
    FileHandler.record_temporary_file('noexist.txt')
    open('junk.txt', 'w').write('junk!')
    FileHandler.record_temporary_file('junk.txt')
    

