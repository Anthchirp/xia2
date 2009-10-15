#!/usr/bin/env python
# Streams.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Maintained by Graeme Winter
# 15th August 2006
# 
# "Standard" output streams for the output of xia2dpa - these will allow 
# filtering of the output to files, the standard output, a GUI, none of 
# the above, all of the above.
# 
# The idea of this is to separate the "administrative", "status" and 
# "scientific" output of the program. Finally I also decided (5/SEP/06)
# to add a stream for "chatter", that is the odds and ends which are 
# going on inside the program which tells you it's doing things.
#
# FIXME 05/SEP/06 wouldn't it be nice to split the output to fit well on 
#                 an 80 character terminal display?
# 
# FIXED 20/OCT/06 would nice to be able to prevent content being echo'd
#                 to the chatter, if possible. Esp. for verbose output
#                 going to say science.
# 
# FIXME 20/OCT/06 need to be able to switch these of to allow nothing to
#                 be printed when running unit tests...

import sys

class _Stream:
    '''A class to represent an output stream. This will be used as a number
    of static instances - Debug and Chatter in particular.'''

    def __init__(self, streamname, prefix):
        '''Create a new stream.'''

        # FIXME would rather this goes to a file...
        # unless this is impossible

        try:
            if streamname == None:
                raise RuntimeError, 'want this to go to stdout'
            self._file = open('%s.txt' % streamname, 'w')
        except:
            self._file = sys.stdout
            
        self._streamname = streamname
        self._prefix = prefix

        self._otherstream = None
        self._off = False

        return

    # FIXED 20/OCT/06 added forward option, specify as false to
    # prevent this happening...
    
    def write(self, record, forward = True):

        if self._off:
            return None
        
        for r in record.split('\n'):
            if self._prefix:
                result = self._file.write('[%s]  %s\n' %
                                          (self._prefix, r.strip()))
            else:
                result = self._file.write('%s\n' %
                                          (r.strip()))

            self._file.flush()

        if self._otherstream and forward:
            self._otherstream.write(record)
        
        return result

    def bigbanner(self, comment, forward = True):
        '''Write a big banner for something.'''

        hashes = '#' * 60

        self.write(hashes, forward)
        self.write('# %s' % comment, forward)
        self.write(hashes, forward)

        return

    def smallbanner(self, comment, forward):
        '''Write a small batter for something, like this:
        ----- comment ------.'''

        dashes = '-' * 10
        
        self.write('%s %s %s' % (dashes, comment, dashes), forward)

        return

    def join(self, otherstream):
        '''Join another stream so that all output from this stream goes also
        to that one.'''

        self._otherstream = otherstream

    def off(self):
        '''Switch the stream writing off...'''

        self._off = True

        return

# FIXME 23/NOV/06 now write a xia2.txt from chatter and rename that
# output stream Stdout... then copy everything there!

Chatter = _Stream('xia2', None)
Stdout = _Stream(None, None)
Debug = _Stream('xia2-debug', None)

Chatter.join(Stdout)

def streams_off():
    '''Switch off the chatter output - designed for unit tests...'''
    Chatter.off()
    return

if __name__ == '__main__':
    Chatter.write('nothing much, really')
