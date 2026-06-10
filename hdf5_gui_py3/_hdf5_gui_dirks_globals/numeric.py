"""Dirks globals: numeric."""

from ._shared import *


__all__ = ['nanavg', 'nanavg_weighted', 'tupleset', 'cumtrapz', 'spearmans_rank', 'kendalls_tau', 'chi2_test', 'rel_ranks', 'bi_exp_copulas', 'par_where', 'val2ind', 'round_to_float', 'nash_sutcliff', 'fourier_approx', 'interp_nan', 'isclose', 'sumup']


def nanavg(x, axis=None, ddof=0):
    ii = np.isfinite(x)
    return (np.nansum(x, axis=axis) /
            (np.sum(ii, axis=axis) - ddof))


def nanavg_weighted(x, axis=None, weights=None):
    if weights is None:
        weights = np.ones_like(x)
    ii = np.isfinite(x)
    weights__ = np.zeros_like(x)
    weights__[ii] = weights[ii]
    return (np.nansum(x * weights, axis=axis) /
            (np.sum(weights__, axis=axis)))


def tupleset(t, i, value):
    l = list(t)
    l[i] = value
    return tuple(l)


def cumtrapz(y, x=None, dx=1.0, axis=-1, initial=None):
    """Cumulatively integrate y(x) using the composite trapezoidal rule.

    Parameters
    - - - - - - - - - -
    y : array_like
    Values to integrate.
    x : array_like, optional
    The coordinate to integrate along. If None (default), use spacing `dx`
    between consecutive elements in `y`.
    dx : int, optional
    Spacing between elements of `y`. Only used if `x` is None.
    axis : int, optional
    Specifies the axis to cumulate. Default is -1 (last axis).
    initial : scalar, optional
    If given, uses this value as the first value in the returned result.
    Typically this value should be 0. Default is None, which means no
    value at ``x[0]`` is returned and `res` has one element less than `y`
    along the axis of integration.

    Returns
    - - - - - - -
    res : ndarray
    The result of cumulative integration of `y` along `axis`.
    If `initial` is None, the shape is such that the axis of integration
    has one less value than `y`. If `initial` is given, the shape is equal
    to that of `y`.

    See Also
    - - - - - - - -
    numpy.cumsum, numpy.cumprod
    quad: adaptive quadrature using QUADPACK
    romberg: adaptive Romberg quadrature
    quadrature: adaptive Gaussian quadrature
    fixed_quad: fixed - order Gaussian quadrature
    dblquad: double integrals
    tplquad: triple integrals
    romb: integrators for sampled data
    trapz: integrators for sampled data
    ode: ODE integrators
    odeint: ODE integrators

    Examples
    - - - - - - - -
    >>> from scipy import integrate
    >>> x = np.linspace(-2, 2, num=20)
    >>> y = x
    >>> y_int = integrate.cumtrapz(y, x)
    >>> #plt.plot(x, y_int, 'ro', x, y[0] + 0.5 * x ** 2, 'b-')
    >>> #plt.show()

    """
    y = np.asarray(y)
    if x is None:
        d = dx
    else:
        d = np.diff(x, axis=axis)

    nd = len(y.shape)
    slice1 = tupleset((slice(None),) * nd, axis, slice(1, None))
    slice2 = tupleset((slice(None),) * nd, axis, slice(None, -1))
    res = np.add.accumulate(d * (y[slice1] + y[slice2]) / 2.0, axis)

    if initial is not None:
        if not np.isscalar(initial):
            raise ValueError("`initial` parameter should be a scalar.")

        shape = list(res.shape)
        shape[axis] = 1
        res = np.concatenate([np.ones(shape, dtype=res.dtype) * initial, res],
                             axis=axis)

    return res


def spearmans_rank(rel_ranks_x, rel_ranks_y):
    """Spearmans rho of relative ranks."""
    n = len(rel_ranks_x)
    return (12. / (n * (n + 1) * (n - 1)) *
            np.sum((rel_ranks_x * n + .5) *
                   (rel_ranks_y * n + .5)) -
            3. * (n + 1) / (n - 1))


def kendalls_tau(x, y):
    """Kendall's Rank correlation coefficient. See Hartung p.599f

    Examples
    --------
    >>> A = [8, 6, 5, 3.5, 1, 2, 3.5, 7]
    >>> B = [6, 7.5, 4, 1, 2, 3, 5, 7.5]
    >>> kendalls_tau(A, B)
    0.5714285714285714
    """
    assert len(x) == len(y)
    x, y = np.asarray(x), np.asarray(y)
    n = len(x)
    # TODO: we have to be pessimistic when coming across equal values
    y_xrank_sorted = y[np.argsort(x)]
    y_ranks = stats.rankdata(y_xrank_sorted)
    # i forcefully put in "<" instead of "<=" because i am annoyed that the
    # correlation between a variable and itself is not 1 when there are
    # equal values inside
    # comment on the comment: changed that back to do it "by the book"
    q_i = np.array([np.sum(y_ranks[ii + 1:] <= y_ranks[ii])
                    for ii in range(n)], dtype=float)
    return 1 - 4 * np.sum(q_i) / (n * (n - 1))


def chi2_test(x, y, k=None, n_parameters=0):
    """Chi-square test for inequality.
    H0: x and y were sampled from the same distribution.

    Parameters
    ----------
    k : int
        Number of classes (bins)

    Returns
    -------
    p_value : float
    """
    n = len(x)
    if k is None:
        k = int(n ** .5)
        # k = n_parameters + 2
    observed, bins = np.histogram(x, k)[:2]
    expected = np.histogram(y, bins)[0]
    chi_test = np.sum((observed.astype(float) - expected) ** 2 / expected)
    # degrees of freedom:
    dof = k - n_parameters - 1
    print(chi_test, stats.chi2.ppf(.95, dof))
    return stats.chisqprob(chi_test, dof)


def rel_ranks(values):
    """Returns ranks of values in the range [0,1]."""
    return (stats.stats.rankdata(values) - .5) / len(values)


def bi_exp_copulas(values1, values2, *args, **kwds):
    """Shows a scatter plot of the emperical copulas of values1 and values2."""
    assert len(values1) == len(values2), "Values must have equal length."
    plt.scatter(rel_ranks(values1), rel_ranks(values2), *args, **kwds)
    plt.xlim(xmin=0, xmax=1)
    plt.ylim(ymin=0, ymax=1)


def par_where(values1, comparison, values2, n_processes=None):
    """Look for values2 in values1 using np.where.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([0, 1, 1, 2, 3])
    >>> b = np.array([1, 2])
    >>> par_where(a, "==", b)  # doctest: +SKIP
    array([1, 2, 3])
    >>> par_where(a, "<", 1)  # doctest: +SKIP
    array([0])

    >>> a = np.zeros(1000000)
    >>> a[[10000, 50000, 75000]] = 1
    >>> par_where(a, "==", 1)
    array([10000, 50000, 75000])
    """
    if n_processes is None:
        n_processes = multiprocessing.cpu_count()

    request_queue = multiprocessing.JoinableQueue()
    result_queue = multiprocessing.Queue()
    pool = [WhereWorker(request_queue, result_queue, comparison)
            for ii in range(n_processes)]

    # distribute work by slicing values1
    start_i = None
    stop_i = 0
    # the (maximum) length of a slice. the number of slices should then be the
    # number of processors on the machine
    i_interval = values1.shape[0] // n_processes + 1
    while stop_i is not None:
        if stop_i + i_interval < len(values1):
            stop_i += i_interval
        else:
            stop_i = None
        pool[0].work(values1[start_i:stop_i], values2)
        start_i = stop_i
    # a joined request_queue means that all tasks are done
    request_queue.join()

    # build a task-id -> result mapping out of the result_queue
    id_result = dict(result_queue.get() for ii in range(n_processes))

    # assemble results in the order of values1
    indices_ = np.array([], dtype="int")
    for id_ in sorted(id_result.keys()):
        # the workers do not see the whole values1-array, so the indices
        # have to be shifted to fit to the length of values1 again
        indices_ = np.r_[indices_, id_result[id_] + id_ * i_interval]

    # signify the workers to break out of their "infinite" loop
    for worker in pool:
        worker.go_home()

    def kill_worker(worker):
        """Asks the worker to join and annoys it recursively until it does.
        Kind of like the unions do with new employees"""
        try:
            worker.join()
        except OSError:
            kill_worker(worker)
    for worker in pool:
        kill_worker(worker)

    return indices_


def val2ind(values, value):
    """Return the index of the nearest neighbor of value in values."""
    # the int-conversion is necessary.  without it, the index comes out as
    # 'numpy.int64' (on my machine), which causes "illegal subscript type"
    # errors when used as an index on netcdf-arrays.
    flat_index = int(np.argmin(np.abs(values - value)))
    if np.ndim(values) == 1:
        return flat_index
    else:
        return np.unravel_index(flat_index, values.shape)


def round_to_float(values, precision):
    """Round to nearest precision.

    >>> round_to_float([8, 12], 5.)
    array([ 10.,  10.])
    """
    values = np.asarray(values, dtype=float)
    rest = values % precision
    return np.where(rest > precision / 2.,
                    values + (precision - rest),
                    values - rest)


def nash_sutcliff(modelled, observed):
    """Nash-Sutcliff efficency.

    >>> import numpy as np
    >>> mod = np.array([1, 1, 1])
    >>> obs = np.array([2, np.nan, 1])
    >>> nash_sutcliff(mod, obs)
    -1.0

    >>> mod = np.array([np.nan, 1, 1])
    >>> nash_sutcliff(mod, obs)
    1.0
    """
    return (1 - np.nansum((modelled - observed) ** 2) /
            np.nansum((observed - np.nanmean(observed)) ** 2))


def fourier_approx(data, order=4, size=None):
    """Approximate data with a Fourier transform, using the order number of
    frequencies with the highest amplitudes.

    Parameters
    ----------
    data : 1-dim ndarray
    order : int, optional
        Number of frequencies to account for.
    size : int, optional
        Desired length of the output. If None, it will be the same as data.
    """
    if size is None:
        size = len(data)
    data_freq = np.fft.fft(data)
    # find the order biggest amplitudes
    ii_below = np.argsort(np.abs(data_freq))[:len(data_freq) - order - 1]
    pars = np.copy(data_freq)
    pars[ii_below] = 0
    return np.fft.irfft(pars, size)


def interp_nan(values, times=None, max_interp=None):
    """Remove nans from values by linear interpolation.

    Parameters
    ----------
    values : ndarray
    times : ndarray, optional
    max_interp : int
        Maximum number of subsequent nans to interpolate over.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([0., np.nan, 1., np.nan, np.nan, 4.])
    >>> interp_nan(a)
    array([ 0. ,  0.5,  1. ,  2. ,  3. ,  4. ])
    >>> interp_nan(a, max_interp=1)
    array([ 0. ,  0.5,  1. ,  nan,  nan,  4. ])
    >>> a = np.arange(6, dtype=float).reshape((2, 3))
    >>> a[0, 1] = np.nan
    >>> interp_nan(a)
    array([[ 0.,  1.,  2.],
           [ 3.,  4.,  5.]])
    """
    values = np.atleast_2d(np.copy(values))
    for row_i, row in enumerate(values):
        nans = np.isnan(row)
        if times is None:
            times = np.arange(values.shape[1])

        if max_interp:
            nan_beginnings = np.where(np.diff(nans.astype(int)) == 1)[0] + 1
            nan_endings = np.where(np.diff(nans.astype(int)) == -1)[0] + 1
            if nans[0]:
                nan_beginnings = np.concatenate(([0], nan_beginnings))
            if nans[-1]:
                nan_endings = np.concatenate((nan_endings, [len(nans) - 1]))

            nan_lengths = nan_endings - nan_beginnings
            for episode_i, nan_length in enumerate(nan_lengths):
                if nan_length > max_interp:
                    start_i = nan_beginnings[episode_i]
                    nans[start_i:start_i + nan_length] = False

        if np.any(nans):
            values[row_i, nans] = \
                np.interp(times[nans], times[~nans], row[~nans])
    return np.squeeze(values)


def isclose(a, b, rtol=1.e-5, atol=1.e-8, equal_nan=False):
    """
    This is stolen from numpy 1.7. Throw it out as soon that version is around!

    Returns a boolean array where two arrays are element-wise equal within a
    tolerance.

    The tolerance values are positive, typically very small numbers.  The
    relative difference (`rtol` * abs(`b`)) and the absolute difference
    `atol` are added together to compare against the absolute difference
    between `a` and `b`.

    Parameters
    ----------
    a, b : array_like
        Input arrays to compare.
    rtol : float
        The relative tolerance parameter (see Notes).
    atol : float
        The absolute tolerance parameter (see Notes).
    equal_nan : bool
        Whether to compare NaN's as equal.  If True, NaN's in `a` will be
        considered equal to NaN's in `b` in the output array.

    Returns
    -------
    y : array_like
        Returns a boolean array of where `a` and `b` are equal within the
        given tolerance. If both `a` and `b` are scalars, returns a single
        boolean value.

    See Also
    --------
    allclose

    Notes
    -----
    .. versionadded:: 1.7.0

    For finite values, isclose uses the following equation to test whether
    two floating point values are equivalent.

     absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))

    The above equation is not symmetric in `a` and `b`, so that
    `isclose(a, b)` might be different from `isclose(b, a)` in
    some rare cases.

    Examples
    --------
    >>> np.isclose([1e10,1e-7], [1.00001e10,1e-8])
    array([ True, False], dtype=bool)
    >>> np.isclose([1e10,1e-8], [1.00001e10,1e-9])
    array([ True,  True], dtype=bool)
    >>> np.isclose([1e10,1e-8], [1.0001e10,1e-9])
    array([False,  True], dtype=bool)
    >>> np.isclose([1.0, np.nan], [1.0, np.nan])
    array([ True, False], dtype=bool)
    >>> np.isclose([1.0, np.nan], [1.0, np.nan], equal_nan=True)
    array([ True,  True], dtype=bool)
    """
    from numpy.core.numeric import seterr, less_equal

    def within_tol(x, y, atol, rtol):
        err = seterr(invalid='ignore')
        try:
            result = less_equal(abs(x - y), atol + rtol * abs(y))
        finally:
            seterr(**err)
        if np.isscalar(a) and np.isscalar(b):
            result = bool(result)
        return result

    x = np.array(a, copy=False, subok=True, ndmin=1)
    y = np.array(b, copy=False, subok=True, ndmin=1)
    xfin = np.isfinite(x)
    yfin = np.isfinite(y)
    if all(xfin) and all(yfin):
        return within_tol(x, y, atol, rtol)
    else:
        finite = xfin & yfin
        cond = np.zeros_like(finite, subok=True)
        # Because we're using boolean indexing, x & y must be the same shape.
        # Ideally, we'd just do x, y = broadcast_arrays(x, y). It's in
        # lib.stride_tricks, though, so we can't import it here.
        x = x * np.ones_like(cond)
        y = y * np.ones_like(cond)
        # Avoid subtraction with infinite/nan values...
        cond[finite] = within_tol(x[finite], y[finite], atol, rtol)
        # Check for equality of infinite values...
        cond[~finite] = (x[~finite] == y[~finite])
        if equal_nan:
            # Make NaN == NaN
            cond[np.isnan(x) & np.isnan(y)] = True
        return cond


def sumup(values, width=24, times_=None, drop_extra=True, mean=False,
          middle_time=True, sum_to_nan=False, acceptable_nans=6,
          max_interp=3):
    """Sum up width number of values along the rows. If there are surplus
    entries, they are dropped as if they were hot (Snoop Dog et al).

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10.).reshape((2, 5))
    >>> a
    array([[ 0.,  1.,  2.,  3.,  4.],
           [ 5.,  6.,  7.,  8.,  9.]])
    >>> sumup(a, 2)
    array([[  1.,   5.],
           [ 11.,  15.]])
    >>> sumup(a, 2, drop_extra=False)
    array([[  1.,   5.,   8.],
           [ 11.,  15.,  18.]])
    >>> sumup(a.ravel(), 5)
    array([ 10.,  35.])
    >>> a[0, 0] = np.nan
    >>> sumup(a, 2, mean=True)
    array([[ 1. ,  2.5],
           [ 5.5,  7.5]])
    """
    width = int(width)
    if max_interp > 0 and not sum_to_nan:
        values = interp_nan(values, max_interp=max_interp)
    if len(values.shape) == 1:
        values = values[np.newaxis, :]
    # we hack the values into a (x, width) shape, sum along the rows and
    # reshape it back
    orig_rows, orig_columns = values.shape
    surplus_columns = orig_columns % width
    if drop_extra and surplus_columns:
        values = values[:, :-surplus_columns]
        orig_columns -= surplus_columns
    elif (not drop_extra) and surplus_columns:
        last_values_mean = values[:, np.newaxis,
                                  - surplus_columns:].mean(axis=2)
        last_values_mean = np.array(last_values_mean, dtype=values.dtype)
        values = np.concatenate((values, last_values_mean), axis=1)
    values = values.reshape((values.size // width, width))
    summed_values = np.nansum(values, axis=1)

    if np.sum(np.isnan(values)) > 0:
        nan_counts = np.sum(np.isnan(values), axis=1)
        if sum_to_nan:
            summed_values[nan_counts > 0] = np.nan
        else:
            nan_ii = (nan_counts > 0) & (nan_counts <= acceptable_nans)
            summed_values[nan_ii] *= \
                width / (float(width) - nan_counts[nan_ii])
            summed_values[nan_counts > acceptable_nans] = np.nan
    if mean:
        summed_values = summed_values.astype(float)
        summed_values /= width - np.sum(np.isnan(values), axis=1)

    new_columns = int(np.ceil(float(orig_columns) / width))
    summed_values = summed_values.reshape((orig_rows, new_columns))

    if times_ is not None:
        if middle_time:
            # use the time in the middle between the data points
            time_shift = round(width / 2.)
        else:
            time_shift = None
        times_ = times_[time_shift::width][:summed_values.shape[1]]
        return np.squeeze(summed_values), times_
    else:
        return np.squeeze(summed_values)

