# LIBTBX_SET_DISPATCHER_NAME xia2.setup

import os
import sys

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from xia2.Applications import xia2setup

if __name__ == '__main__':
  xia2setup.run()