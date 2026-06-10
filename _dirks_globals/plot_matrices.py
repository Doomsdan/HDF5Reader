"""Dirks globals: plot matrices."""

from ._shared import *


__all__ = ['splom', 'cplom', 'vplom', 'asymmetry1', 'asymmetry2', 'ccplom']


def splom(data, variable_names=None, f_kwds=None, h_kwds=None, s_kwds=None,
          opacity=.1, highlight_mask=None, ticklabels=True, figsize=None,
          hists=True, facecolor=(0, .5, .5), edgecolor=(1, 1, 1),
          f_opacity=None, e_opacity=None, highlight_color="red"):
    """Scatter-plot matrix with interactive capabilities.

    Parameters
    ----------
    data : (K,T) ndarray
        K variables, T timesteps
    variable_names : sequence of strings, optional
        Used to label the subplots.
    f_kwds : dictionary, optional
        Keyword arguments that are passed to plt.subplots.
    h_kwds : dictionary, optional
        Keyword arguments that are passed to the histogramm calls.
    s_kwds : dictionary, optional
        Keyword arguments that are passed to the scatter calls.
    opacity : float, optional
        Opacity used for edgecolor parameter of scatter call.
    highlight_mask : (T,) boolean ndarray, optional
        Mask of timesteps that will be highlighted in the scatter plots.
    ticklabels : boolean, optional
        Set to False to supress displaying x- and yticklabels.
    figsize : None or tuple of width, height, optional
        Size of the figure.
    hists : boolean, optional
        Plot histograms on the main diagonal.
    """
    cc = mpl.colors.ColorConverter()

    def switch_fc(artist, ind):
        fc = artist._facecolors
        if len(fc) == 1:
            fc = np.array(len(artist._offsets) * fc.tolist())
        fc[ind] = 1 - fc[ind]
        return fc

    def brush(event):
        """Highlight points in all plots."""
        # cache the collections. we will hopefully not get any more subplots
        if not hasattr(brush, "collections"):
            brush.collections = [sub.collections[0]
                                 for sub in fig.get_children()
                                 if hasattr(sub, "collections")
                                 and len(sub.collections) == 1]
        # handle the click on a histogram bin
        if type(event.artist) is mpl.patches.Rectangle:
            event.artist._facecolor = \
                tuple(1 - color_comp for color_comp in event.artist._facecolor)
            # find the indices of the points within the bin clicked on
            lower = event.artist._x
            upper = lower + event.artist._width
            values = data[event.artist.axes.var_i].ravel()
            ind = np.where((values > lower) & (values <= upper))
        else:
            # handle the click on a single scatter point
            ind = event.ind
        for col in brush.collections:
            col._facecolors = switch_fc(col, ind)
        fig.canvas.draw()

    f_kwds = {} if f_kwds is None else f_kwds
    h_kwds = {} if h_kwds is None else h_kwds
    s_kwds = {} if s_kwds is None else s_kwds
    f_opacity = opacity if f_opacity is None else f_opacity
    e_opacity = opacity if e_opacity is None else e_opacity
    data = np.asarray(data)
    n_variables = data.shape[0]
    figsize = plt.rcParams["figure.figsize"] if figsize is None else figsize
    fig, axes = square_subplots(n_variables, figsize=figsize, **f_kwds)

    for ii in range(n_variables):
        for jj in range(n_variables):
            if ii == jj:
                if hists:
                    axes[ii, jj].hist(np.where(np.isnan(data[ii]), 0,
                                               data[ii]),
                                      min(20, int(len(data[ii]) ** .5)),
                                      picker=5, normed=True,
                                      # want to achieve red when inverting
                                      facecolor=cc.to_rgba(facecolor, alpha=0),
                                      **h_kwds)
                    # store the ii-index as an attribute to identify the
                    # variable later in the brush function
                    axes[ii, jj].var_i = ii
                else:
                    fig.delaxes(axes[ii, jj])
            else:
                if highlight_mask is None:
                    facecolors = cc.to_rgba(facecolor, alpha=f_opacity)
                else:
                    facecolors = np.empty((data.shape[1], 4))
                    facecolors[highlight_mask] = cc.to_rgba(highlight_color,
                                                            f_opacity)
                    # want to achieve red when inverting
                    facecolors[~highlight_mask] = cc.to_rgba(facecolor,
                                                             f_opacity)
                axes[ii, jj].scatter(data[jj], data[ii], picker=5,
                                     facecolors=facecolors,
                                     edgecolors=cc.to_rgba(edgecolor,
                                                           e_opacity),
                                     **s_kwds)
# show ticklabels only on the margins
#                if (jj != 0) or (ii == jj):
#                    axes[ii, jj].set_yticklabels("")
#                if ii != n_variables - 1:
#                    axes[ii, jj].set_xticklabels("")
            if variable_names and jj == 0:
                axes[ii, jj].set_ylabel(variable_names[ii])
            if variable_names and ii == n_variables - 1:
                axes[ii, jj].set_xlabel(variable_names[jj])
            if not ticklabels:
                axes[ii, jj].set_yticks([])
                axes[ii, jj].set_xticks([])

    fig.canvas.mpl_connect("pick_event", brush)
    return fig


def cplom(data, variable_names=None, h_kwds=None, s_kwds=None, title=None,
          opacity=.1, scatter=True, hist=True, **fig_kwds):
    """Copula-plot matrix. Data is assumed to be a 2 dim arrays with
    observations in rows."""
    from lhglib.contrib.veathergenerator.Clausulas.CopIntDiffCont \
        import emp_density_copula_plot as cop
    h_kwds = {} if h_kwds is None else h_kwds
    s_kwds = {} if s_kwds is None else s_kwds
    data = np.asarray(data)
    n_variables = data.shape[0]
    fig, axes = plt.subplots(n_variables, n_variables, **fig_kwds)
    ranks = np.array([rel_ranks(var) for var in data])
    for ii in range(n_variables):
        for jj in range(n_variables):
            if ii == jj:
                if hist:
                    axes[ii, jj].hist(data[ii], 20, normed=True,
                                      facecolor=(0, 0, 0, 0), **h_kwds)
                else:
                    axes[ii, jj].axis("off")
                axes[ii, jj].set_xticks([])
                axes[ii, jj].set_yticks([])
            else:
                cop(ranks[jj], ranks[ii], ax=axes[ii, jj], **s_kwds)
                if scatter:
                    axes[ii, jj].scatter(ranks[jj], ranks[ii], marker="o",
                                         facecolors=(0, 0, 0, 0),
                                         edgecolors=(0, 0, 0, opacity))
                axes[ii, jj].set_aspect("equal")
                axes[ii, jj].set_xticks([])
                axes[ii, jj].set_yticks([])
            if variable_names and jj == 0:
                axes[ii, jj].set_ylabel(variable_names[ii])
            if variable_names and ii == n_variables - 1:
                axes[ii, jj].set_xlabel(variable_names[jj])
    if title:
        plt.suptitle(title)
    return fig, axes


def vplom(data, variable_names=None, h_kwds=None, s_kwds=None, title=None,
          opacity=.1, scatter=True, **fig_kwds):
    """Copula-plot matrix. Every bivariate copula is variable over delta
    variable (sometimes looks like a "v").
    Data is assumed to be a 2 dim arrays with observations in rows."""
    from lhglib.contrib.veathergenerator.Clausulas.CopIntDiffCont \
        import emp_density_copula_plot as cop
    h_kwds = {} if h_kwds is None else h_kwds
    s_kwds = {} if s_kwds is None else s_kwds
    data = np.asarray(data)
    n_variables = data.shape[0]
    fig, axes = plt.subplots(n_variables, n_variables, **fig_kwds)
    ranks_data = np.array([rel_ranks(var)[1:] for var in data])
    ranks_diff = np.array([rel_ranks(np.diff(var)) for var in data])
    for ii in range(n_variables):
        for jj in range(n_variables):
            x, y = ranks_diff[jj], ranks_data[ii]
            cop(x, y, ax=axes[ii, jj], **s_kwds)
            if scatter:
                axes[ii, jj].scatter(x, y, marker="o",
                                     facecolors=(0, 0, 0, 0),
                                     edgecolors=(0, 0, 0, opacity))
            axes[ii, jj].set_aspect("equal")
            axes[ii, jj].set_xticks([])
            axes[ii, jj].set_yticks([])
            if variable_names and jj == 0:
                axes[ii, jj].set_ylabel(variable_names[ii])
            if variable_names and ii == n_variables - 1:
                axes[ii, jj].set_xlabel(r"$\Delta$ %s" % variable_names[jj])
    if title:
        plt.suptitle(title)
    return fig, axes


def asymmetry1(u1, u2):
    xx = u1 - .5
    yy = u2 - .5
    return np.mean(xx * yy * (xx + yy))


def asymmetry2(u1, u2):
    xx = u1 - .5
    yy = u2 - .5
    return np.mean(-xx * yy * (xx - yy))


def ccplom(data, k=1, variable_names=None, h_kwds=None, s_kwds=None,
           title=None, opacity=.1, cmap=None, x_bins=20, y_bins=20,
           display_rho=True, display_asy=True, vmax_fct=1.,
           **fig_kwds):
    """Cross-Copula-plot matrix. Values that appear on the x-axes are shifted
    back k timesteps. Data is assumed to be a 2 dim arrays with
    observations in rows."""
    data = np.asarray(data)
    K, T = data.shape
    h_kwds = {} if h_kwds is None else h_kwds
    s_kwds = {} if s_kwds is None else s_kwds
    n_variables = data.shape[0]
    fig, axes = plt.subplots(n_variables, n_variables,
                             subplot_kw=dict(aspect="equal"),
                             **fig_kwds)
    ranks = np.array([rel_ranks(var) for var in data])
    x_slice = slice(None, None if k == 0 else -k)
    y_slice = slice(k, None)
    for ii in range(n_variables):
        for jj in range(n_variables):
            ax = axes[ii, jj]
            ranks_x = ranks[jj, x_slice]
            ranks_y = ranks[ii, y_slice]
            hist2d(ranks_x, ranks_y, x_bins, y_bins,
                   ax=ax, cmap=cmap, scatter=False)
            ax.scatter(ranks_x, ranks_y,
                       marker="o", facecolors=(0, 0, 0, 0),
                       edgecolors=(0, 0, 0, opacity), **s_kwds)
            if display_rho:
                rho = spearmans_rank(ranks_x, ranks_y)
                ax.text(.5, .5, r"$\rho = %.3f$" % rho,
                        horizontalalignment="center")
            if display_asy:
                asy1 = asymmetry1(ranks_x, ranks_y)
                asy2 = asymmetry2(ranks_x, ranks_y)
                ax.text(.5, .75, r"$a_1 = %.3f$" % asy1,
                        horizontalalignment="center")
                ax.text(.5, .25, r"$a_2 = %.3f$" % asy2,
                        horizontalalignment="center")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.grid(False)
            # show ticklabels only on the margins
            if jj != 0:
                ax.set_yticklabels("")
            if ii != n_variables - 1:
                ax.set_xticklabels("")
            if jj == 0:
                ax.set_ylabel(variable_names[ii] + "(t)")
            if ii == n_variables - 1:
                ax.set_xlabel(variable_names[jj] + "(t-%d)" % k)
    # reset the vlims, so that we have the same color scale in all plots
    for ax in np.ravel(axes):
        for im in ax.get_images():
            im.set_clim(vmax=vmax_fct * hist2d.h_max)
    if title:
        plt.suptitle(title)
    else:
        plt.suptitle("k = %d" % k)
    hist2d.clear_cache()
    return fig, axes

