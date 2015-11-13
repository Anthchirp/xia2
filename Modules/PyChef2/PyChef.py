from __future__ import division

import math
from collections import Mapping
from cctbx.array_family import flex
from iotbx.data_plots import table_data
from libtbx import phil


phil_scope = phil.parse("""\
d_min = None
  .type = float(value_min=0)
d_max = None
  .type = float(value_min=0)
resolution_bins = 8
  .type = int
anomalous = False
  .type = bool
range {
  width = 1
    .type = float(value_min=0)
  min = None
    .type = float(value_min=0)
  max = None
    .type = float(value_min=0)
}
batch
  .multiple = True
{
  range = None
    .type = ints(value_min=0, size=2)
  dose_start = None
    .type = float(value_min=0)
  dose_step = None
    .type = float(value_min=0)
}
""")


class observation_group(object):

  PLUS = 1
  MINUS = -1
  CENTRIC = 0

  def __init__(self, asu_index, is_centric, iplus=None, iminus=None):
    self._asu_index = asu_index
    self._centric = is_centric
    if iplus is None:
      iplus = flex.size_t()
    if iminus is None:
      iminus = flex.size_t()
    self._iplus = iplus
    self._iminus = iminus

  def add_iplus(self, iplus):
    self._iplus.append(iplus)

  def add_iminus(self, iminus):
    self._iminus.append(iminus)

  @property
  def iminus(self):
    return self._iminus

  @property
  def iplus(self):
    return self._iplus

  @property
  def asu_index(self):
    return self._asu_index

  def is_centric(self):
    return self._centric


class unmerged_observations(Mapping):

  def __init__(self, unmerged_intensities):
    self._intensities_original_index = unmerged_intensities

    self._observations = {}
    from cctbx import miller, sgtbx
    sg = self._intensities_original_index.space_group()
    sg_type = sg.type()
    asu = sgtbx.reciprocal_space_asu(sg_type)
    anomalous_flag = self._intensities_original_index.anomalous_flag()

    ma = self._intensities_original_index
    original_indices = ma.indices()
    unique_indices = original_indices.deep_copy()
    isym = flex.int(unique_indices.size())

    miller.map_to_asu_isym(sg_type, anomalous_flag, unique_indices, isym)

    n_plus, n_minus = 0, 0

    for iref in range(len(original_indices)):
      h_orig = original_indices[iref]
      h_uniq = unique_indices[iref]
      h_isym = isym[iref]

      h_eq = miller.sym_equiv_indices(sg, h_uniq)
      if h_eq.is_centric():
        flag = observation_group.CENTRIC
      else:
        asu_which = asu.which(h_uniq)
        assert asu_which != 0
        if asu_which == 1:
          flag = observation_group.PLUS
        else:
          flag = observation_group.MINUS
          h_uniq = tuple(-1*h for h in h_uniq)

      group = self._observations.get(h_uniq)
      if group is None:
        group = observation_group(
          h_uniq, is_centric=(flag == observation_group.CENTRIC))
        self._observations[h_uniq] = group
      if flag == observation_group.MINUS:
        n_minus += 1
        group.add_iminus(iref)
      else:
        n_plus += 1
        group.add_iplus(iref)

  def __iter__(self):
    return self._observations.iteritems()

  def __getitem__(self, hkl):
    return self._observations[hkl]

  def __len__(self):
    return len(self._observations)

  def __contains__(self, hkl):
    return hkl in self._observations


class statistics(object):

  def __init__(self, intensities, dose, n_bins=8,
               range_min=None, range_max=None, range_width=1):

    self.intensities = intensities
    self.dose = dose
    self.n_bins = n_bins
    self.range_min = range_min
    self.range_max = range_max
    self.range_width = range_width
    assert self.range_width > 0

    if self.range_min is None:
      self.range_min = flex.min(self.dose) - self.range_width
    if self.range_max is None:
      self.range_max = flex.max(self.dose)
    self.n_steps = 2 + int((self.range_max - self.range_min) - self.range_width)

    sel = (self.dose.as_double() <= self.range_max) & (self.dose.as_double() >= self.range_min)
    self.dose = self.dose.select(sel)

    self.intensities = self.intensities.select(sel)
    self.d_star_sq = self.intensities.d_star_sq().data()

    self.binner = self.intensities.setup_binner_d_star_sq_step(
      d_star_sq_step=(flex.max(self.d_star_sq)-flex.min(self.d_star_sq)+1e-8)/self.n_bins)

    self.observations = unmerged_observations(self.intensities)

  def calc_completeness_vs_dose(self):

    iplus_count = [flex.double(self.n_steps, 0) for i in xrange(self.n_bins)]
    iminus_count = [flex.double(self.n_steps, 0) for i in xrange(self.n_bins)]
    ieither_count = [flex.double(self.n_steps, 0) for i in xrange(self.n_bins)]
    iboth_count = [flex.double(self.n_steps, 0) for i in xrange(self.n_bins)]

    for h_uniq, observed in self.observations:
      #if observed.is_minus():
        #continue

      #irefs = list(observed.irefs)
      dose_min_iplus = self.range_max + self.range_width
      dose_min_iminus = self.range_max + self.range_width

      if observed.iplus.size():
        i_bin = self.binner.get_i_bin(self.d_star_sq[observed.iplus[0]]) - 1
      else:
        i_bin = self.binner.get_i_bin(self.d_star_sq[observed.iminus[0]]) - 1

      if i_bin < 0:
        continue

      for i, i_ref in enumerate(observed.iplus):
        dose_i = self.dose[i_ref]
        dose_min_iplus = min(dose_i, dose_min_iplus)
        if observed.is_centric():
          dose_min_iminus = min(dose_i, dose_min_iminus)

      for i, i_ref in enumerate(observed.iminus):
        assert i_ref not in observed.iplus
        dose_i = self.dose[i_ref]
        dose_min_iminus = min(dose_i, dose_min_iminus)

      start_iplus = int((dose_min_iplus - self.range_min)/self.range_width)
      start_iminus = int((dose_min_iminus - self.range_min)/self.range_width)

      if start_iplus < self.n_steps:
        iplus_count[i_bin][start_iplus] += 1
      if start_iminus < self.n_steps:
        iminus_count[i_bin][start_iminus] += 1
      if min(start_iplus, start_iminus) < self.n_steps:
        ieither_count[i_bin][min(start_iplus, start_iminus)] += 1
      if max(start_iplus, start_iminus) < self.n_steps:
        iboth_count[i_bin][max(start_iplus, start_iminus)] += 1

    # now accumulate as a function of time

    for i_bin in xrange(self.n_bins):
      for j in range(1, self.n_steps):
        iplus_count[i_bin][j] += iplus_count[i_bin][j - 1]
        iminus_count[i_bin][j] += iminus_count[i_bin][j - 1]
        ieither_count[i_bin][j] += ieither_count[i_bin][j - 1]
        iboth_count[i_bin][j] += iboth_count[i_bin][j - 1]

    # accumulate as a function of dose and resolution

    iplus_comp_overall = flex.double(self.n_steps, 0)
    iminus_comp_overall = flex.double(self.n_steps, 0)
    ieither_comp_overall = flex.double(self.n_steps, 0)
    iboth_comp_overall = flex.double(self.n_steps, 0)

    binner_non_anom = self.intensities.as_non_anomalous_array().use_binning(
      self.binner)
    n_complete = binner_non_anom.counts_complete()[1:-1]

    for i_bin in xrange(self.n_bins):
      iplus_comp_overall += iplus_count[i_bin]
      iminus_comp_overall += iminus_count[i_bin]
      ieither_comp_overall += ieither_count[i_bin]
      iboth_comp_overall += iboth_count[i_bin]

      iplus_count[i_bin] /= n_complete[i_bin]
      iminus_count[i_bin] /= n_complete[i_bin]
      ieither_count[i_bin] /= n_complete[i_bin]
      iboth_count[i_bin] /= n_complete[i_bin]

    tot_n_complete = sum(n_complete)
    iplus_comp_overall /= tot_n_complete
    iminus_comp_overall /= tot_n_complete
    ieither_comp_overall /= tot_n_complete
    iboth_comp_overall /= tot_n_complete

    from libtbx import group_args
    return group_args(
      iplus_comp_bins=iplus_count,
      iminus_comp_bins=iminus_count,
      ieither_comp_bins=ieither_count,
      iboth_comp_bins=iboth_count,
      iplus_comp_overall=iplus_comp_overall,
      iminus_comp_overall=iminus_comp_overall,
      ieither_comp_overall=ieither_comp_overall,
      iboth_comp_overall=iboth_comp_overall)

  def calc_rcp_scp(self):

    A = [[0] * self.n_steps for i in xrange(self.n_bins)]
    B = [[0] * self.n_steps for i in xrange(self.n_bins)]
    isigma = [[0] * self.n_steps for i in xrange(self.n_bins)]
    count = [[0] * self.n_steps for i in xrange(self.n_bins)]

    intensities_data = self.intensities.data()
    sigmas = self.intensities.sigmas()

    def accumulate(irefs, i_bin):
      if i_bin < 0:
        return
      for i, i_ref in enumerate(irefs):
        dose_i = self.dose[i_ref]
        I_i = intensities_data[i_ref]
        sigi_i = sigmas[i_ref]
        for j, j_ref in enumerate(irefs[i+1:]):
          I_j = intensities_data[j_ref]
          sigi_j = sigmas[j_ref]
          A_part = math.fabs(I_i - I_j)
          B_part = 0.5 * math.fabs(I_i + I_j)
          dose_j = self.dose[j_ref]
          dose_0 = int((max(dose_i, dose_j) - self.range_min)/self.range_width)
          A[i_bin][dose_0] += A_part
          B[i_bin][dose_0] += B_part
          isigma[i_bin][dose_0] += ((I_i/sigi_i) + (I_j/sigi_j))
          count[i_bin][dose_0] += 2

    for h_uniq, observed in self.observations:
      if len(observed.iplus) > 1:
        i_bin = self.binner.get_i_bin(self.d_star_sq[observed.iplus[0]]) - 1
        accumulate(list(observed.iplus), i_bin)
      if len(observed.iminus) > 1:
        i_bin = self.binner.get_i_bin(self.d_star_sq[observed.iminus[0]]) - 1
        accumulate(list(observed.iminus), i_bin)

    # now accumulate as a function of time

    for i_bin in xrange(self.n_bins):
      for j in xrange(1, self.n_steps):
        A[i_bin][j] += A[i_bin][j-1]
        B[i_bin][j] += B[i_bin][j-1]
        isigma[i_bin][j] += isigma[i_bin][j-1]
        count[i_bin][j] += count[i_bin][j-1]

    # accumulate as a function of dose and resolution

    rcp_overall = flex.double(self.n_steps, 0)
    rcp_bins = [flex.double(self.n_steps, 0) for i in range(self.n_bins)]
    scp_overall = flex.double(self.n_steps, 0)
    scp_bins = [flex.double(self.n_steps, 0) for i in range(self.n_bins)]

    for j in xrange(self.n_steps):

      for i_bin in xrange(self.n_bins):
        top = A[i_bin][j]
        bottom = B[i_bin][j]

        rcp = 0.0
        scp = 0.

        if bottom > 0:
          rcp = top/bottom
          if count[i_bin][j] > 100:
            isig = isigma[i_bin][j] / count[i_bin][j]
            scp = rcp / (1.1284 / isig)

          rcp_bins[i_bin][j] = rcp
          scp_bins[i_bin][j] = scp

      ot = sum(A[i_bin][j] for i_bin in xrange(self.n_bins))
      ob = sum(B[i_bin][j] for i_bin in xrange(self.n_bins))

      if ob > 0:
        overall = ot/ob
      else:
        overall = 0.
      rcp_overall[j] = overall

      scp_overall[j] = sum(scp_bins[i_bin][j] for i_bin in xrange(self.n_bins))/self.n_bins
    return rcp_bins, rcp_overall, scp_bins, scp_overall

  def calc_rd(self):

    rd_top = [0] * self.n_steps
    rd_bottom = [0] * self.n_steps

    intensities_data = self.intensities.data()
    sigmas = self.intensities.sigmas()

    for h_uniq, observed in self.observations:
      irefs = list(observed.iplus) + list(observed.iminus)
      if len(irefs) == 1:
        # lone observation, no pairs
        continue
      for i, i_ref in enumerate(irefs):
        dose_i = self.dose[i_ref]
        I_i = intensities_data[i_ref]
        for j, j_ref in enumerate(irefs[i+1:]):
          I_j = intensities_data[j_ref]
          dose_j = self.dose[j_ref]
          d_dose = int(
            round(math.fabs(dose_i - dose_j) - self.range_min)/self.range_width)
          rd_top[d_dose] += math.fabs(I_i - I_j)
          rd_bottom[d_dose] += 0.5 * (I_i + I_j)

    rd = flex.double(rd_top[i]/rd_bottom[i] if rd_bottom[i] > 0 else 0
                     for i in xrange(self.n_steps))
    return rd

  def print_completeness_vs_dose(self, completeness_vs_dose):

    anomalous = self.intensities.anomalous_flag()

    title = "Completeness vs. BATCH:"
    graph_names = ["Completeness", "Completeness in resolution shells"]

    if anomalous:
      column_labels = ["BATCH"] + ["%.2f-%.2f(A)" %self.binner.bin_d_range(i+1)
                                   for i in range(self.n_bins)] + \
        ['I+', 'I-', 'I', 'dI']
      column_formats = ["%8.1f"] + ["%5.3f" for i in range(self.n_bins)] + ["%5.3f", "%5.3f", "%5.3f", "%5.3f"]
      #graph_columns = [[0,1,2,3,4]]
      graph_columns = [[0] + range(self.n_bins+2, self.n_bins+5), range(self.n_bins+1)]
    else:
      column_labels = ["BATCH"] + ["%.2f-%.2f(A)" %self.binner.bin_d_range(i+1)
                                   for i in range(self.n_bins)] + ["I"]
      column_formats = ["%8.1f"] + ["%5.3f" for i in range(self.n_bins)] + [ "%5.3f"]
      graph_columns = [[0, self.n_bins+1], range(self.n_bins+1)]

    table_completeness = table_data(title=title,
                                    column_labels=column_labels,
                                    column_formats=column_formats,
                                    graph_names=graph_names,
                                    graph_columns=graph_columns)
    res = completeness_vs_dose
    for i in xrange(self.n_steps):
      if anomalous:
        row = [i * self.range_width + self.range_min] \
          + [res.ieither_comp_bins[i_bin][i] for i_bin in range(self.n_bins)] \
          + [res.iplus_comp_overall[i], res.iminus_comp_overall[i],
             res.ieither_comp_overall[i], res.iboth_comp_overall[i]]
      else:
        row = [i * self.range_width + self.range_min]  \
          + [res.ieither_comp_bins[i_bin][i] for i_bin in range(self.n_bins)] \
          + [res.ieither_comp_overall[i]]
      table_completeness.add_row(row)

    print table_completeness.format_loggraph()

  def print_rcp_vs_dose(self, rcp_bins, rcp_overall):

    assert len(rcp_bins) == self.binner.n_bins_used()
    title = "Cumulative radiation damage analysis:"
    column_labels = ["BATCH"] + ["%.2f-%.2f(A)" %self.binner.bin_d_range(i+1)
                                 for i in range(self.n_bins)] + ["Rcp(d)"]
    column_formats = ["%8.1f"] + ["%7.4f" for i in range(self.n_bins+1)]
    graph_names = ["Rcp(d)", "Rcp(d), in resolution shells"]
    graph_columns = [[0, self.n_bins+1], range(self.n_bins+1)]

    table_rcp = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min] \
        + [rcp_bins[j][i] for j in xrange(len(rcp_bins))] + [rcp_overall[i]]
      table_rcp.add_row(row)

    print table_rcp.format_loggraph()

  def print_scp_vs_dose(self, scp_bins, scp_overall):

    assert len(scp_bins) == self.binner.n_bins_used()
    title = "Normalised radiation damage analysis:"
    column_labels = ["BATCH"] + ["%.2f-%.2f(A)" %self.binner.bin_d_range(i+1)
                                 for i in range(self.n_bins)] + ["Rcp(d)"]
    column_formats = ["%8.1f"] + ["%7.4f" for i in range(self.n_bins+1)]
    graph_names = ["Scp(d)", "Scp(d), in resolution shells"]
    graph_columns = [[0, self.n_bins+1], range(self.n_bins+1)]

    table_scp = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min] \
        + [scp_bins[j][i] for j in xrange(len(scp_bins))] + [scp_overall[i]]
      table_scp.add_row(row)

    print table_scp.format_loggraph()

  def print_rd_vs_dose(self, rd):

    title = "R vs. BATCH difference:"
    column_labels = ["BATCH", "Rd"]
    column_formats = ["%8.1f", "%5.3f"]
    graph_names = ["Rd"]
    graph_columns = [[0,1]]

    table_rd = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min, rd[i]]
      table_rd.add_row(row)

    print table_rd.format_loggraph()


def run(args):
  from iotbx.reflection_file_reader import any_reflection_file

  interp = phil_scope.command_line_argument_interpreter()
  params, unhandled = interp.process_and_fetch(
    args, custom_processor='collect_remaining')
  params = params.extract()
  n_bins = params.resolution_bins

  args = unhandled

  intensities = None
  batches = None

  reader = any_reflection_file(args[0])
  assert reader.file_type() == 'ccp4_mtz'
  arrays = reader.as_miller_arrays(merge_equivalents=False)
  for ma in arrays:
    if ma.info().labels == ['BATCH']:
      batches = ma
    elif ma.info().labels == ['I', 'SIGI']:
      intensities = ma
    elif ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
      intensities = ma

  assert intensities is not None
  assert batches is not None
  mtz_object = reader.file_content()

  indices = mtz_object.extract_original_index_miller_indices()
  intensities = intensities.customized_copy(indices=indices)
  batches = batches.customized_copy(indices=indices)

  range_min = params.range.min
  range_max = params.range.max
  range_width = params.range.width

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()

  if len(params.batch):
    dose = flex.double(batches.size(), -1)
    batch_data = batches.data()
    for batch in params.batch:
      start = batch.dose_start
      step = batch.dose_step
      for i in range(batch.range[0], batch.range[1]+1):
        # inclusive range
        dose.set_selected(batch_data == i, start + step * (i-batch.range[0]))
  else:
    dose = batches.data()

  sel = dose > -1
  intensities = intensities.select(sel)
  dose = dose.select(sel)

  if params.d_min or params.d_max:
    sel = flex.bool(intensities.size(), True)
    d_spacings = intensities.d_spacings().data()
    if params.d_min:
      sel &= d_spacings >= params.d_min
    if params.d_max:
      sel &= d_spacings <= params.d_max
    intensities = intensities.select(sel)
    dose = dose.select(sel)

  stats = statistics(intensities, dose, n_bins=params.resolution_bins,
                     range_min=params.range.min, range_max=params.range.max,
                     range_width=params.range.width)

  completeness_result = stats.calc_completeness_vs_dose()
  rcp_bins, rcp_overall, scp_bins, scp_overall = stats.calc_rcp_scp()
  rd = stats.calc_rd()

  stats.print_completeness_vs_dose(completeness_result)
  stats.print_rcp_vs_dose(rcp_bins, rcp_overall)
  stats.print_scp_vs_dose(scp_bins, scp_overall)
  stats.print_rd_vs_dose(rd)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
