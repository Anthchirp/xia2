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


def exercise_serialization():
  if not have_dials_regression:
    print "Skipping exercise_serialization(): dials_regression not configured"
    return

  from Handlers.CommandLine import CommandLine

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.DialsIndexer import DialsIndexer
  from Modules.Refiner.DialsRefiner import DialsRefiner
  from Modules.Integrater.DialsIntegrater import DialsIntegrater
  from Modules.Scaler.CCP4ScalerA import CCP4ScalerA

  from Schema.XProject import XProject
  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  proj = XProject()
  proj._name = "PROJ1"
  cryst = XCrystal("CRYST1", proj)
  proj.add_crystal(cryst)
  wav = XWavelength("WAVE1", cryst, wavelength=0.98)
  cryst.add_wavelength(wav)
  cryst.set_ha_info({'atom': 'S'})
  directory, image = os.path.split(template %1)
  wav.add_sweep(name='SWEEP1', directory=directory, image=image)

  import json
  from dxtbx.serialize.load import _decode_dict

  sweep = wav.get_sweeps()[0]
  indexer = DialsIndexer()
  indexer.set_working_directory(tmp_dir)
  indexer.setup_from_image(template %1)
  indexer.set_indexer_sweep(sweep)
  sweep._indexer = indexer

  refiner = DialsRefiner()
  refiner.set_working_directory(tmp_dir)
  refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
  sweep._refiner = refiner

  integrater = DialsIntegrater()
  integrater.set_working_directory(tmp_dir)
  integrater.setup_from_image(template %1)
  integrater.set_integrater_refiner(refiner)
  #integrater.set_integrater_indexer(indexer)
  integrater.set_integrater_sweep(sweep)
  integrater.set_integrater_epoch(sweep.get_epoch(1))
  integrater.set_integrater_sweep_name(sweep.get_name())
  integrater.set_integrater_project_info(
    cryst.get_name(), wav.get_name(), sweep.get_name())
  sweep._integrater = integrater

  scaler = CCP4ScalerA()
  scaler.add_scaler_integrater(integrater)
  scaler.set_scaler_xcrystal(cryst)
  scaler.set_scaler_project_info(cryst.get_name(), wav.get_name())
  scaler._scalr_xcrystal = cryst
  cryst._scaler = scaler

  s_dict = sweep.to_dict()
  s_str = json.dumps(s_dict, ensure_ascii=True)
  s_dict = json.loads(s_str, object_hook=_decode_dict)
  xsweep = XSweep.from_dict(s_dict)

  w_dict = wav.to_dict()
  w_str = json.dumps(w_dict, ensure_ascii=True)
  w_dict = json.loads(w_str, object_hook=_decode_dict)
  xwav = XWavelength.from_dict(w_dict)
  assert xwav.get_sweeps()[0].get_wavelength() is xwav

  c_dict = cryst.to_dict()
  c_str = json.dumps(c_dict, ensure_ascii=True)
  c_dict = json.loads(c_str, object_hook=_decode_dict)
  xcryst = XCrystal.from_dict(c_dict)
  assert xcryst.get_xwavelength(xcryst.get_wavelength_names()[0]).get_crystal() is xcryst

  p_dict = proj.to_dict()
  p_str = json.dumps(p_dict, ensure_ascii=True)
  p_dict = json.loads(p_str, object_hook=_decode_dict)
  xproj = XProject.from_dict(p_dict)
  assert xproj.get_crystals().values()[0].get_project() is xproj

  json_str = proj.as_json()
  xproj = XProject.from_json(string=json_str)
  assert xproj.get_crystals().values()[0].get_project() is xproj
  print xproj.get_output()
  print "\n".join(xproj.summarise())
  json_str = xproj.as_json()
  xproj = XProject.from_json(string=json_str)
  assert xproj.get_crystals().values()[0].get_project() is xproj
  xcryst = xproj.get_crystals().values()[0]
  intgr = xcryst._get_integraters()[0]
  assert intgr.get_integrater_finish_done()
  assert xcryst._get_scaler()._sweep_handler.get_sweep_information(
    intgr.get_integrater_epoch()).get_integrater() is intgr

  print xproj.get_output()
  print "\n".join(xproj.summarise())
  print


def run(args):
  exercise_serialization()
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
