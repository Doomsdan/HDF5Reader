"""Dirks globals: plot scales."""

from ._shared import *


__all__ = ['scale_yticks', 'yscale_figs', 'xscale_figs', 'yscale_subplots']


def scale_yticks(event):
    """Automagically make room for yticklabels.
    Use it like this:
        fig = gcf()
        fig.canvas.mpl_connect('draw_event', scale_yticks)

    Stolen from the matplotlib-howto.  Slightly changed, so it is possible to
    separate the function from the calling code.
    http://matplotlib.sourceforge.net/faq/howto_faq.html\
    #automatically-make-room-for-tick-labels
    """
    labels = plt.gca().get_yticklabels()
    fig = plt.gcf()
    bboxes = []
    for label in labels:
        bbox = label.get_window_extent()
        # the figure transform goes from relative coords->pixels and we
        # want the inverse of that
        bboxi = bbox.inverse_transformed(fig.transFigure)
        bboxes.append(bboxi)

    # this is the bbox that bounds all the bboxes, again in relative
    # figure coords
    bbox = mpl.transforms.Bbox.union(bboxes)
    if fig.subplotpars.left < bbox.width:
        # we need to move it over
        fig.subplots_adjust(left=1.1 * bbox.width)  # pad a little
        fig.canvas.draw()
    return False


def yscale_figs(per_type=True, regrid=False, figs=None):
    """Set a common y-scale to all open figures (or only of those passed in
    figs). If per_type is set to True, y-scales are distinguished by the type
    of the subplots."""
    if per_type:
        key_func = type
    else:
        key_func = lambda x: "the one to rule them all"

    # see http://matplotlib.sourceforge.net/faq/howto_faq.html#\
    # find-all-objects-in-figure-of-a-certain-type
    ylim_getable = lambda sub: hasattr(sub, "get_ylim")
    ylim_setable = lambda sub: hasattr(sub, "set_ylim")

    # find the y-limits of each subplot
    ymins, ymaxs = {}, {}
    if figs is None:
        figs = [plt.figure(fig_num) for fig_num in plt.get_fignums()]
    for fig in figs:
        for subplot in fig.findobj(ylim_getable):
            ymin, ymax = subplot.get_ylim()
            sub_type = key_func(subplot)
            if sub_type not in ymins:
                ymins[sub_type], ymaxs[sub_type] = [], []
            ymins[sub_type].append(ymin)
            ymaxs[sub_type].append(ymax)

    # find the extremes for each type of subplot
    ymin, ymax = {}, {}
    for sub_type in ymins.keys():
        ymin[sub_type] = min(ymins[sub_type])
        ymax[sub_type] = max(ymaxs[sub_type])

    # set ylims
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        for subplot in fig.findobj(ylim_setable):
            sub_type = key_func(subplot)
            try:
                subplot.set_ylim(ymin=ymin[sub_type], ymax=ymax[sub_type])
            except (TypeError, KeyError):
                pass
        if regrid:
            try:
                subplot.set_rgrids(np.linspace(1e-6, ymax[sub_type], 10))
            except AttributeError:
                pass


def xscale_figs(per_type=True, regrid=False, figs=None):
    """Set a common x-scale to all open figures (or only of those passed in
    figs). If per_type is set to True, x-scales are distinguished by the type
    of the subplots."""
    if per_type:
        key_func = type
    else:
        key_func = lambda x: "the one to rule them all"

    # see http://matplotlib.sourceforge.net/faq/howto_faq.html#\
    # find-all-objects-in-figure-of-a-certain-type
    xlim_getable = lambda sub: hasattr(sub, "get_xlim")
    xlim_setable = lambda sub: hasattr(sub, "set_xlim")

    # find the x-limits of each subplot
    xmins, xmaxs = {}, {}
    if figs is None:
        figs = [plt.figure(fig_num) for fig_num in plt.get_fignums()]
    for fig in figs:
        for subplot in fig.findobj(xlim_getable):
            xmin, xmax = subplot.get_xlim()
            sub_type = key_func(subplot)
            if sub_type not in xmins:
                xmins[sub_type], xmaxs[sub_type] = [], []
            xmins[sub_type].append(xmin)
            xmaxs[sub_type].append(xmax)

    # find the extremes for each type of subplot
    xmin, xmax = {}, {}
    for sub_type in xmins.keys():
        xmin[sub_type] = min(xmins[sub_type])
        xmax[sub_type] = max(xmaxs[sub_type])

    # set xlims
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        for subplot in fig.findobj(xlim_setable):
            sub_type = key_func(subplot)
            try:
                subplot.set_xlim(xmin=xmin[sub_type], xmax=xmax[sub_type])
            except (TypeError, KeyError):
                pass
        if regrid:
            try:
                subplot.set_rgrids(np.linspace(1e-6, xmax[sub_type], 10))
            except AttributeError:
                pass


def yscale_subplots(fig=None, per_type=False, regrid=False):
    """Sets a common y-scale to all subplots.  If per_type is set to True,
    y-scales are distinguished by the type of the subplots."""
    if fig is None:
        fig = plt.gcf()

    if per_type:
        key_func = type
    else:
        key_func = lambda x: "the one to rule them all"

    # see http://matplotlib.sourceforge.net/faq/howto_faq.html#\
    # find-all-objects-in-figure-of-a-certain-type
    ylim_getable = lambda sub: hasattr(sub, "get_ylim")
    ylim_setable = lambda sub: hasattr(sub, "set_ylim")

    # find the y-limits of each subplot
    ymins, ymaxs = {}, {}
    for subplot in fig.findobj(ylim_getable):
        ymin, ymax = subplot.get_ylim()
        sub_type = key_func(subplot)
        if sub_type not in ymins:
            ymins[sub_type], ymaxs[sub_type] = [], []
        ymins[sub_type].append(ymin)
        ymaxs[sub_type].append(ymax)

    # find the extremes for each type of subplot
    ymin, ymax = {}, {}
    for sub_type in ymins.keys():
        ymin[sub_type] = min(ymins[sub_type])
        ymax[sub_type] = max(ymaxs[sub_type])

    # set ylims (and reset grids)
    for subplot in fig.findobj(ylim_setable):
        sub_type = key_func(subplot)
        try:
            subplot.set_ylim(ymin=ymin[sub_type], ymax=ymax[sub_type])
        except TypeError:
            pass
        if regrid:
            subplot.set_rgrids(np.linspace(1e-6, ymax[sub_type], 10))

