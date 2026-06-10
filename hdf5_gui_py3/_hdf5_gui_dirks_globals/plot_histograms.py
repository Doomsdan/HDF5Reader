"""Dirks globals: plot histograms."""

from ._shared import *


__all__ = ['time_hist', 'kde_gauss', 'hist', 'hist2d']


def time_hist(values, times_=None, ylabel=None, figsize=None, trend=False,
              *args, **kwds):
    """Plot a time-series horizontally with a vertical histogram on the right.
    Stolen in part from:
    http://matplotlib.sourceforge.net/examples/axes_grid/scatter_hist.html"""
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    fig = plt.figure(figsize=figsize)

    if times_ is None:
        times_ = np.arange(len(values))
    ax = fig.add_subplot(111)
    plt.plot(times_, values, "-x", *args, **kwds)
    if trend:
        dummy_time = np.arange(len(values))
        b, a = stats.linregress(dummy_time, values)[:2]
        plt.plot(times_, a + b * dummy_time, "r")
    plt.ylabel(ylabel)
    plt.grid()

    # create new axes on the right and on the top of the current axes
    # The first argument of the new_vertical(new_horizontal) method is
    # the height (width) of the axes to be created in inches.
    divider = make_axes_locatable(ax)
    hist_ax = divider.append_axes("right", 1.2, pad=0.1, sharey=ax)
    hist_ax.hist(values, 40, orientation="horizontal")  # , *args, **kwds)
    hist_ax.set_xticks([], [])
    for ytickl in hist_ax.get_yticklabels():
        ytickl.set_visible(False)
    return fig, (ax, hist_ax)


def kde_gauss(dataset, evaluation_points=None, kernel_width=None,
              maxopt=500, return_width=False, verbose=False):
    """

    Parameter
    ---------
    dataset : (T,) ndarray
        input data as array of length T
    evaluation points : (N,) ndarray, optional if return_width=True
        N points as array (e.g. xx=np.linspace(-3,3,100)
    kernel_width : float, optional
        kernel_width (eg 0.3) if set, no MLM-routine to infer optimal kernel
        width
    maxopt : int, optional
        size of sample to optimize kernel_width, affects runtime strongly.
        depends on memorysize. max 1000 with 2GB mem
    return_width : boolean, optional
        Return the optimized kernel width and nothing else.
    verbose : boolean, optional
        Print information (also from the optimizer).

    Example
    -------
        dataset = np.array(np.random.normal(size=1e3))
        xx = np.linspace(-3,3, 1e3)
        plt.plot(xx,kde_gauss(dataset,xx))
    """
    def residual_matrix(x_vec, y_vec):
        """Returns a matrix with residuals (x:horizontal,y:vertical)"""
        x_vec, y_vec = map(np.asarray, (x_vec, y_vec))
        return x_vec[None, :] - y_vec[:, None]

    def neglog_likelihood(kernel_width, dataset, verbose=False):
        """optimizing kernel width with MLM leave one out"""

        optMatrix = residual_matrix(dataset, dataset)
        if NE:
            pi = np.pi
            ne_str = ("1.0 / (sqrt(2 * pi) * kernel_width) / "
                      "exp(optMatrix ** 2 / (2 * kernel_width ** 2))")
            optMatrix = ne.evaluate(ne_str)
        else:
            preTerm = 1.0 / (np.sqrt(2 * np.pi) * kernel_width)
            optMatrix = preTerm / np.exp(optMatrix ** 2 /
                                         (2 * kernel_width ** 2))
        nDataset = np.shape(dataset)[0]
        # sets diagonal to 0, i.e. leave-one-out method
        optMatrix.ravel()[::nDataset + 1] = 0
        densities = np.sum(optMatrix, axis=1) / float(nDataset - 1)
        # LN if <>0 for MLM
        d_sum = 0
        err = 0
        for d in densities:
            if d > 0:
                d_sum -= np.log(d)
            else:
                if err == 0:
                    if verbose:
                        print("LN(0) case do attend")
                    err = 1
                d_sum += 100  # not nice
        return d_sum

    dataset = np.asarray(dataset)
    # problem bei optimierung: d fluktuiert und haengt von maxopt ab
    # je hoeher maxopt desto kleiner d!
    dataset = np.sort(dataset)

    # optimizing kernel width if d=None
    if kernel_width is None:
        data_width = dataset.max() - dataset.min()
        d_0 = data_width / 10
        if d_0 < 0.0001:
            d_0 = 0.0001
        if len(dataset) > 1000:
            fluct = True  # while values fluctuate, repeat iteration
            d_n = []  # list of d's
            d_act, d_old = d_0, 0
            n_min = 8 + np.sqrt(len(dataset) / maxopt)  # min nr of iterations
            n_act = 0

            while fluct or n_act <= n_min:
                dataset_sample = random.sample(dataset, maxopt)
                d_n.append(optimize.fmin(neglog_likelihood, d_act,
                                         args=(dataset_sample, verbose),
                                         disp=verbose)[0])
                d_act = sum(d_n) / float(len(d_n))
                # stop if fluct < 1%
                if abs(d_act - d_old) / float(d_act) < 0.01:
                    fluct = False
                if verbose:
                    print(d_act, d_old, d_n[-1])
                d_old = d_act
                n_act += 1
            kernel_width = d_act

        else:
            dataset_sample = dataset
            kernel_width = optimize.fmin(neglog_likelihood, d_0,
                                         args=(dataset_sample, verbose),
                                         disp=verbose)
        if verbose:
            print('Kernelwidth = %f' % kernel_width)

    if return_width:
        return kernel_width

    evaluation_points = np.asarray(evaluation_points)

    if len(dataset) < len(evaluation_points):
        print ('Caution: you get more ev. points than input data\
        be aware of pseudo exactness')

    # save kernel width, so it can be retrieved if anyone is interested
    kde_gauss.kernel_width = kernel_width

    # creating Matrix with residuals
#    kdeMatrix = residual_matrix(dataset,evaluation_points)
#    sparse_kde_mask = kdeMatrix < .001
#    from scipy.sparse import lil_matrix
#    sparse_kde = lil_matrix(kdeMatrix.shape)
#    sparse_kde[sparse_kde_mask] = kdeMatrix[sparse_kde_mask]
#     using Gaussian kernel
#    import numexpr as ne
#    preTerm = ne.evaluate("1.0 / ((2 * math.pi)**.5 * kernel_width)")
#    kdeMatrix = preTerm / np.exp(kdeMatrix ** 2 / (2 * kernel_width ** 2))

    if len(dataset) * len(evaluation_points) > 1e7:
        parts = int(len(dataset) * len(evaluation_points) / 1e7) + 1
        brIncr = int(len(evaluation_points) / parts)
        densities = np.array([])
        for i in range(parts + 1):
            if verbose:
                print('part %i of %i' % (i, parts))
            kdeMatrix = \
                residual_matrix(dataset,
                                evaluation_points[i * brIncr:(i + 1) * brIncr])
            preTerm = 1.0 / (np.sqrt(2 * np.pi) * kernel_width)
            kdeMatrix = (preTerm /
                         np.exp(kdeMatrix ** 2 / (2 * kernel_width ** 2)))
            tmp_densities = np.sum(kdeMatrix, axis=1) / float(len(dataset))
            densities = np.hstack((densities, tmp_densities))
    else:
        kdeMatrix = residual_matrix(dataset, evaluation_points)
        preTerm = 1.0 / (np.sqrt(2 * np.pi) * kernel_width)
        kdeMatrix = preTerm / np.exp(kdeMatrix ** 2 / (2 * kernel_width ** 2))
        # suming lines
        densities = np.sum(kdeMatrix, axis=1) / float(len(dataset))
    return densities


def hist(values, n_bins, dist=None, pdf=None, kde=False, fig=None,
         ax=None, discrete=False, figsize=None, legend=True, *args,
         **kwds):
    """Plots a histogram and therotical or empirical densities."""
    try:
        if np.any(~np.isfinite(values)):
            warnings.warn("Non-finite values in values.")
    except TypeError:
        pass
    figsize = plt.rcParams["figure.figsize"] if figsize is None else figsize
    if ax is None:
        fig = plt.figure(figsize=figsize) if fig is None else fig
        axes = ax1 = fig.add_subplot(111)
    else:
        axes = ax1 = ax

    # the histogram of the data
    if discrete:
        values_2d = np.atleast_2d(values)
        bin_offset = -.5 * values_2d.shape[0]
        for i, values in enumerate(values_2d):
            values = np.array(values)
            bins = np.arange(values.min(), values.max() + 1, dtype=int)
            bins = bins + bin_offset + i
            freqs = np.bincount(values.astype(int))
            freqs = freqs[freqs >= bins.min()]
            freqs = freqs.astype(float) / values.size
            ax1.vlines(bins, 0, freqs, linewidth=3)
            ax1.set_xlim(bins[0] - 1, bins[-1] + 1)
    else:
        bins = ax1.hist(values, n_bins, normed=True, facecolor='grey',
                        alpha=0.75, *args, **kwds)[1]

    ax1.set_ylabel("relative frequency")

    if not (isinstance(values, list) or values.ndim == 2):
        values_2d = values,
    else:
        values_2d = values

    if discrete:
        eva_points = bins
    else:
        eva_points = np.linspace(bins[0], bins[-1], 4 * n_bins)
    if kde:
        for val_i, values in enumerate(values_2d):
            density = kde_gauss(values, eva_points)
            ax1.plot(eva_points, density, label=("kde%d" % val_i))
    if dist:
        try:
            dist[0]
            dists = dist
        except TypeError:
            dists = dist,

        # the quantile part
        ax2 = ax1.twinx()
        axes = [ax1, ax2]
        for values in values_2d:
            # empirical cdf
            values_sort = np.sort(values)
            ranks_emp = (.5 + np.arange(len(values))) / len(values)
            ax2.plot(values_sort, ranks_emp)
            pdf = []
            for dist in dists:
                if hasattr(dist, "fit"):
                    fitted_dist = dist(*dist.fit(values))
                else:
                    fitted_dist = dist
                pdf += [fitted_dist.pdf]
                # theoretical cdf
                ranks_theory = fitted_dist.cdf(eva_points)
                p_val = stats.kstest(values, fitted_dist.cdf, mode="asymp")[1]
                ax2.plot(eva_points, ranks_theory, '--',
                         label="%s p-value: %.1f%%" % (dist.name, p_val * 100))
                ax2.set_ylabel(r"cumulative frequency")
                ax2.grid()

        if len(dists) == 1:
            if hasattr(dist, "parameter_names"):
                plt.title(" ".join("%s:%.3f" % (par_name, par)
                                   for par_name, par
                                   in zip(dist.parameter_names,
                                          fitted_dist.params)))
            elif hasattr(fitted_dist, "args"):
                plt.title(" ".join("%.3f" % par for par in fitted_dist.args))
        elif len(dists) > 1 and legend:
            plt.legend(loc="best")
    if pdf:
        try:
            pdf[0]
            pdfs = pdf
        except TypeError:
            pdfs = (pdf,)
        for pdf in pdfs:
            density_th = pdf(eva_points)
            if discrete:
                density_th *= len(values)
            ax1.plot(eva_points, density_th, '--o' if discrete else '--',
                     linewidth=1, label="pdf")

    if fig is not None:
        return fig, axes
    else:
        axes


def hist2d(x, y, n_xbins=15, n_ybins=15, kind="img", ax=None, cmap=None,
           scatter=True, opacity=.6, vmax=None):
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = plt.gcf()
    if cmap is None:
        cmap = plt.get_cmap("coolwarm")
    H, xedges, yedges = np.histogram2d(x, y, (n_xbins, n_ybins), normed=True)
    # if this histogram is part of a plot-matrix, the plot-matrix
    # might want to set vmax to a common value.  expose h_max to the
    # outside here as a function attribute for that reason.
    h_max = np.max(H)
    if h_max > hist2d.h_max:
        hist2d.h_max = h_max
    if kind == "contourf":
        x_bins = .5 * (xedges[1:] + xedges[:-1])
        y_bins = .5 * (yedges[1:] + yedges[:-1])
        ax.contourf(x_bins, y_bins, H.T, cmap=cmap, vmin=0, vmax=vmax)
    elif kind == "img":
        ax.imshow(H.T,
                  extent=(xedges[0], xedges[-1], yedges[0], yedges[-1]),
                  origin="left", aspect="equal", interpolation="none",
                  cmap=cmap, vmin=0, vmax=vmax)
        x = (x - x.min() - .5 / n_xbins) * n_xbins
        y = (y - y.min() - .5 / n_ybins) * n_ybins
    if scatter:
        ax.scatter(x, y, marker="o", facecolors=(0, 0, 0, 0),
                   edgecolors=(0, 0, 0, opacity))
    return fig, ax

