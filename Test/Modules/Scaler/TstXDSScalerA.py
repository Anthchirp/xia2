

import os
import sys
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

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_xds_scaler(nproc=None):
  if not have_dials_regression:
    print "Skipping exercise_xds_scaler(): dials_regression not configured"
    return

  if nproc is not None:
    from xia2.Handlers.Flags import Flags
    Flags.set_parallel(nproc)

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.XDSIndexer import XDSIndexer
  from Modules.Integrater.XDSIntegrater import XDSIntegrater
  from Modules.Scaler.XDSScalerA import XDSScalerA
  indexer = XDSIndexer()
  indexer.set_working_directory(tmp_dir)
  indexer.setup_from_image(template %1)

  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
  directory, image = os.path.split(template %1)
  sweep = XSweep('SWEEP1', wav, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)

  integrater = XDSIntegrater()
  integrater.set_working_directory(tmp_dir)
  integrater.setup_from_image(template %1)
  integrater.set_integrater_indexer(indexer)
  integrater.set_integrater_sweep(sweep)
  integrater.set_integrater_sweep_name('SWEEP1')
  integrater.set_integrater_project_info('CRYST1', 'WAVE1', 'SWEEP1')

  scaler = XDSScalerA()
  scaler.add_scaler_integrater(integrater)
  scaler.set_scaler_xcrystal(cryst)
  scaler.set_scaler_project_info('CRYST1', 'WAVE1')

  check_scaler_files_exist(scaler)

  # test serialization of scaler
  json_str = scaler.as_json()
  #print json_str
  scaler2 = XDSScalerA.from_json(string=json_str)
  scaler2.set_scaler_xcrystal(cryst)

  check_scaler_files_exist(scaler2)

  scaler2.set_scaler_finish_done(False)
  check_scaler_files_exist(scaler2)

  scaler2.set_scaler_done(False)
  check_scaler_files_exist(scaler2)

  scaler2._scalr_integraters = {} # XXX
  scaler2.add_scaler_integrater(integrater)
  scaler2.set_scaler_prepare_done(False)
  check_scaler_files_exist(scaler2)


def check_scaler_files_exist(scaler):
  merged = scaler.get_scaled_merged_reflections()
  for filetype in ('mtz', 'sca', 'sca_unmerged'):
    assert merged.has_key(filetype)
    if isinstance(merged[filetype], basestring):
      files = [merged[filetype]]
    else:
      files = merged[filetype].values()
    for f in files:
      assert os.path.isfile(f)



def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_xds_scaler(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
