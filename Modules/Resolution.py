#!/usr/bin/env python
# Resolution.py
# 
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th June, 2008
# 
# A module which, given an unmerged reflection file, will read through and
# calculate the distribution of I/sigma from unmerged reflections as a 
# function of resolution, along with quartiles (25%, 75%) which may help
# to make decisions when the data are anisotropic.
#

import sys
import os
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory

factory = CCP4Factory()

def compute_resolution(distance, offset, wavelength):
    '''Compute the resolution (d spacing) for the provided sample to
    detector distance, offset on the detector and wavelength. This assumes
    that the detector is orthogonal to the direct beam.'''

    theta = 0.5 * math.atan(offset / distance)
    dspacing = 0.5 * wavelength / math.sin(theta)

    return dspacing

def prepare_mtz(hklin, hklout):
    '''Prepare an MTZ file for resolution analysis - this will sort & sum
    the reflections found therein.'''

    hkltemp = 'hkltemp.mtz'

    sort = factory.Sortmtz()
    sort.set_hklin(hklin)
    sort.set_hklout(hkltemp)
    sort.sort()

    scala = factory.Scala()
    scala.set_hklin(hkltemp)
    scala.set_hklout(hklout)
    scala.sum()

def read_mtz(mtz_file, pixel_mm, distance, wavelength, beam_mm):
    '''Read an MTZ file output by Moslfm - this is slightly confused by the 
    need to sum the partials, which will be done by sorting, running scala
    with a spell to output unmerged with scale constant... this will however
    need a working directory and temporary file names! suddenly this gets
    complicated... Not unless I code a separate prepare_mtz method.'''

    # first transform the beam centre to pixel values
    
    beam_x = beam_mm[0] / pixel_mm[0]
    beam_y = beam_mm[1] / pixel_mm[1]

    # now read all of the reflections using mtzdump

    mtzdump = factory.Mtzdump()
    mtzdump.set_hklin(mtz_file)
    reflections = mtzdump.dump_mosflm_intensities()

    result = []

    for lst in reflections:
        i = lst[3]
        sigma = lst[4]
        x = pixel_mm[0] * (lst[6] - beam_x)
        y = pixel_mm[1] * (lst[7] - beam_y)

        offset = math.sqrt(x * x + y * y)

        resolution = compute_resolution(distance, offset, wavelength)

        result.append((i, sigma, resolution))

    return result

def read_xds_ascii(xds_ascii_file, pixel_mm, distance, wavelength, beam_mm):
    '''Read the records in an XDS_ASCII.HKL reflection file and
    output a list of i, sigma, resolution for external processing.'''

    beam_x = beam_mm[1] / pixel_mm[0]
    beam_y = beam_mm[0] / pixel_mm[1]

    result = []

    for record in open(xds_ascii_file, 'r').readlines():
        if '!' in record:
            continue

        lst = record.split()

        i = float(lst[3])
        sigma = float(lst[4])
        x = pixel_mm[1] * (float(lst[5]) - beam_x)
        y = pixel_mm[0] * (float(lst[6]) - beam_y)

        offset = math.sqrt(x * x + y * y)

        resolution = compute_resolution(distance, offset, wavelength)

        result.append((i, sigma, resolution))

    return result

def nint(a):
    '''Standard nearest integer calculation.'''

    i = int(a)

    if a > 0:
        if a - i > 0.5:
            i += 1
    else:
        if a - i < -0.5:
            i -= 1

    return i

def sort_resolution(reflections):
    '''Sort the reflections as (resolution, isigma).'''

    result = []

    for r in reflections:
        result.append((r[2], r[1] / r[1]))

    result.sort()

    return result

def sph_kernel(r, h):
    '''A cubic spline SPH kernel in one dimension.'''

    if r < 0:
        raise RuntimeError, 'negative r'

    if h < 0:
        raise RuntimeError, 'negative h'

    x = r / h
    k = 13.0 / 12.0

    if x > 2:
        return 0

    if x > 1:
        return k * 0.25 * math.pow(2 - x, 3)

    return k * (1 - 1.5 * math.pow(x, 2) + 0.75 * math.pow(x, 3))

def sph_smooth(reflections, nrefl):
    '''Using an SPH-like scheme, calculate the smoothed distribution of
    I/sigma across the (nearly) whole resolution range.'''

    # first pass - work out the bin sizes etc.

    nbins = nint((1.0 / nrefl) * len(reflections))

    # first find min, max resolution

    dmin = reflections[0][2]
    dmax = dmin

    for r in reflections:
        d = r[2]
        if d > dmax:
            dmax = d
        if d < dmin:
            dmin = d

    # now divide the region into N bins in 1/d^2 spacing

    smin = 1.0 / (dmax * dmax)
    smax = 1.0 / (dmin * dmin)
    sd = (smax - smin)

    # now generate the sorted list of I/sigma values

    r2 = sort_resolution(reflections)

    # now need to calculate a density for each point

    density = []

    for r in r2:
        pass
        

def bin_resolution(reflections, nrefl):
    '''Get an average (and quartiles) I/sigma as a function of resolution,
    binned to give equally spaced bins with an average of about nrefl
    reflections.'''

    # first guess nbins

    nbins = nint((1.0 / nrefl) * len(reflections))

    # first find min, max resolution

    dmin = reflections[0][2]
    dmax = dmin

    for r in reflections:
        d = r[2]
        if d > dmax:
            dmax = d
        if d < dmin:
            dmin = d

    # now divide the region into N bins in 1/d^2 spacing

    smin = 1.0 / (dmax * dmax)
    smax = 1.0 / (dmin * dmin)
    sd = (smax - smin)

    # now allocate the reflections

    bins = []

    resol = []

    for j in range(nbins + 1):
        bins.append([])
        resol.append((1.0 / math.sqrt(smin + sd * j / float(nbins)),
                      1.0 / math.sqrt(smin + sd * (j + 1) / float(nbins))))

    for r in reflections:
        isigma = r[0] / r[1]
        s = 1.0 / (r[2] * r[2])
        bin = nint(nbins * (s - smin) / sd)
        bins[bin].append(isigma)

    # now calculate the means, quartiles

    means = []
    q25 = []
    q75 = []
    count = []

    for j in range(nbins + 1):
        bins[j].sort()

        l = len(bins[j])
        ql = l / 4
        means.append(sum(bins[j]) / l)
        q25.append(bins[j][ql])
        q75.append(bins[j][-ql])
        count.append(l)

    return resol, means, q25, q75, count
    
if __name__ == '__main__':

    # first test XDS file reading etc.

    xds_ascii = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'UnitTest', 'Modules',
                             'Resolution', 'XDS_ASCII.HKL')

    xds_beam_pixel = 1158.7, 1157.6
    xds_beam = 94.46, 94.54
    xds_distance = 156.88
    xds_wavelength = 0.9790
    xds_pixel = 0.0816, 0.0816

    refl = read_xds_ascii(xds_ascii, xds_pixel, xds_distance,
                          xds_wavelength, xds_beam)
    
    resol, means, q25, q75, count = bin_resolution(refl, 1000)

    for j in range(len(resol)):
        print '%6.2f %6.2f %6.2f %6.2f %6.2f %6d' % \
              (resol[j][0], resol[j][1], means[j], q25[j], q75[j], count[j])

    # then make the same test with the mosflm output

    if False:
    
        mtz_file = os.path.join(os.environ['X2TD_ROOT'],
                                'Test', 'UnitTest', 'Modules',
                                'Resolution', 'resolution_test.mtz')
        
        mtz_beam = 94.46, 94.54
        mtz_distance = 156.88
        mtz_wavelength = 0.9790
        mtz_pixel = 0.0816, 0.0816
        
        # first prepare the reflections
        
        prepare_mtz(mtz_file, 'temp.mtz')
        
        # then read & compute
        
        refl = read_mtz('temp.mtz', mtz_pixel, mtz_distance,
                        mtz_wavelength, mtz_beam)
        
        resol, means, q25, q75, count = bin_resolution(refl, 1000)
        
        for j in range(len(resol)):
            print '%6.2f %6.2f %6.2f %6.2f %6.2f %6d' % \
                  (resol[j][0], resol[j][1], means[j],
                   q25[j], q75[j], count[j])
    
