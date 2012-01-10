#!/usr/bin/env python
# 
# Biostruct-X Data Reduction Use Case 1.2:
# 
# Validate reflection data from test integration code against data from XDS,
# by means of computing a correlaton coefficient between the two.

import math
import random
from cctbx.array_family import flex
from annlib_ext import AnnAdaptor as ann_adaptor
from scitbx import matrix

def meansd(values):

    assert(len(values) > 3)
    
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / (len(values) - 1)
    
    return mean, math.sqrt(var)

def cc(a, b):

    assert(len(a) == len(b))
    
    ma, sa = meansd(a)
    mb, sb = meansd(b)

    r = (1 / (len(a) - 1)) * sum([((a[j] - ma) / sa) * ((b[j] - mb) / sb)
                                  for j in range(len(a))])

    return r

def work_cc():

    a = [random.random() + 0.01 * j for j in range(1000)]
    b = [random.random() + 0.01 * j for j in range(1000)]

    return cc(a, b) 

def test_ann():

    reference = flex.double()

    for j in range(3 * 100):
        reference.append(random.random())
    
    query = flex.double()

    for j in range(3 * 10):
        query.append(random.random())

    ann = ann_adaptor(data = reference, dim = 3, k = 1)
    ann.query(query)

    # workout code - see how far separated on average they are - which should
    # in principle decrease as the number of positions in the reference set
    # increases

    offsets = []

    for j in range(10):
        q = matrix.col([query[3 * j + k] for k in range(3)])
        r = matrix.col([reference[3 * ann.nn[j] + k] for k in range(3)])
        offsets.append((q - r).length())

    print meansd(offsets)
        

if __name__ == '__main__':
    test_ann()

    

    
