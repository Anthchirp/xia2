
import os
import sys
import shutil

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Wrappers.XIA.Integrate import Integrate as XIA2Integrate

from Handlers.Streams import Chatter, Debug

def process_one_sweep(args):


  assert len(args) == 1
  args = args[0]
  #stop_after = args.stop_after

  command_line_args = args.command_line_args
  nproc = args.nproc
  crystal_id = args.crystal_id
  wavelength_id = args.wavelength_id
  sweep_id = args.sweep_id
  failover = args.failover
  driver_type = args.driver_type

  from Driver.DriverFactory import DriverFactory
  default_driver_type = DriverFactory.get_driver_type()
  DriverFactory.set_driver_type(driver_type)

  curdir = os.path.abspath(os.curdir)

  if '-xinfo' in command_line_args:
    idx = command_line_args.index('-xinfo')
    del command_line_args[idx+1]
    del command_line_args[idx]

  xia2_integrate = XIA2Integrate()

  #import tempfile
  #tmpdir = tempfile.mkdtemp(dir=curdir)
  import uuid
  tmpdir = os.path.join(curdir, str(uuid.uuid4()))
  os.makedirs(tmpdir)
  xia2_integrate.set_working_directory(tmpdir)
  xia2_integrate.add_command_line_args(args.command_line_args)
  xia2_integrate.set_phil_file(os.path.join(curdir, 'xia2-working.phil'))
  xia2_integrate.add_command_line_args(['sweep.id=%s' %sweep_id])
  xia2_integrate.set_nproc(nproc)
  xia2_integrate.set_njob(1)
  xia2_integrate.set_mp_mode('serial')

  output = None
  success = False

  try:
    xia2_integrate.run()
    output = get_sweep_output_only(xia2_integrate.get_all_output())
    success = True
  except Exception, e:
    if failover:
      Chatter.write('Processing sweep %s failed: %s' % \
                    (sweep_id, str(e)))
    else:
      #print e
      raise
  finally:
    from Schema.XProject import XProject
    xia2_json = os.path.join(tmpdir, 'xia2.json')
    assert os.path.exists(xia2_json)

    sweep_tmp_dir = os.path.join(tmpdir, crystal_id, wavelength_id, sweep_id)
    sweep_target_dir = os.path.join(curdir, crystal_id, wavelength_id, sweep_id)

    # update the absolute paths in the json files
    import fileinput
    for line in fileinput.FileInput(files=[xia2_json], inplace=1):
      line = line.replace(sweep_tmp_dir, sweep_target_dir)
      print line

    move_output_folder(sweep_tmp_dir, sweep_target_dir)
    xinfo = XProject.from_json(xia2_json)
    xcryst = xinfo.get_crystals().values()[0]
    xsweep = xcryst.get_xwavelength(wavelength_id).get_sweeps()[0]
    shutil.rmtree(tmpdir, ignore_errors=True)
    if os.path.exists(tmpdir):
      shutil.rmtree(tmpdir, ignore_errors=True)
    DriverFactory.set_driver_type(default_driver_type)
    return success, output, xsweep.to_dict()

def get_sweep_output_only(all_output):
  sweep_lines = []
  in_sweep = False
  for line in all_output:
    if line.startswith("Processing took "):
      break
    elif in_sweep: sweep_lines.append(line)
    elif line.startswith("Command line: "):
      in_sweep = True
  return "".join(sweep_lines)

def move_output_folder(sweep_tmp_dir, sweep_target_dir):
  """Move contents of xia2 sweep processing folder from sweep_tmp_dir to
     sweep_target_dir, while also updating any absolute path in any xia2.json
     file.
  """
  if os.path.exists(sweep_target_dir):
    shutil.rmtree(sweep_target_dir)
  #print "Moving %s to %s" %(sweep_tmp_dir, sweep_target_dir)
  shutil.move(sweep_tmp_dir, sweep_target_dir)

  # update the absolute paths in the json files
  for folder in ('index', 'refine', 'integrate'):
    json_file = os.path.join(sweep_target_dir, folder, 'xia2.json')
    if os.path.exists(json_file):
      import fileinput
      for line in fileinput.FileInput(files=[json_file], inplace=1):
        line = line.replace(sweep_tmp_dir, sweep_target_dir)
        print line
