"""Dirks globals: plot layout."""

from ._shared import *


__all__ = ['LegendSubtitleHandler', 'square_subplots', 'stacked_plot']


class LegendSubtitleHandler(object):
    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        # this dedents the label
        handlebox.set_width(0)
        # a dummy with zero width and no visible edge
        x0, y0 = handlebox.xdescent, handlebox.ydescent
        patch = mpatches.Rectangle([x0, y0], 0, handlebox.height,
                                   edgecolor=(0, 0, 0, 0),
                                   transform=handlebox.get_transform())
        handlebox.add_artist(patch)
        return patch


def square_subplots(n_variables, *args, **kwds):
    """Similar to plt.subplots, but shares x-axes column-wise and y-axes
    row - wise. Main diagonal subplots only share x-axes."""
    fig = plt.figure(*args, **kwds)
    axes = np.empty((n_variables, n_variables), dtype=object)
    for ii in range(n_variables):
        for jj in range(n_variables):
            if ii == 0:
                sharex_ax = None
            else:
                sharex_ax = axes[0, jj]

            if (jj == 0) or (ii == jj):
                sharey_ax = None
            elif ii == 0:
                sharey_ax = axes[ii, 1]
            else:
                sharey_ax = axes[ii, 0]

            axes[ii, jj] = fig.add_subplot(n_variables, n_variables,
                                           ii * n_variables + jj + 1,
                                           sharex=sharex_ax,
                                           sharey=sharey_ax)
    return fig, axes


def stacked_plot(values, x=None, ylabels=None, with_hist=True, *args, **kwds):
    """Vertically stacked subplots (as seen on Magdalenas screen)."""
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    fig = plt.figure()
    n_plots = values.shape[1]
    sub = None
    if x is None:
        x = np.arange(values.shape[0])
    for plot_i, series in enumerate(values.T):
        sub = fig.add_subplot(n_plots, 1, plot_i + 1, sharex=sub)
        plt.plot(x, series, *args, **kwds)
        if ylabels:
            plt.ylabel(ylabels[plot_i])
        # add a vertical histogram on the right side
        if with_hist:
            divider = make_axes_locatable(sub)
            hist_ax = divider.append_axes("right", 1.2, pad=0.1, sharey=sub)
            hist_ax.hist(values, 40, orientation="horizontal", *args, **kwds)
            hist_ax.set_xticks([], [])
            for ytickl in hist_ax.get_yticklabels():
                ytickl.set_visible(False)

