"""Just some functions I find myself writing or searching for again and
again..."""

# The imports are not all done here.  Importing this module to use a few
# specific functions would mean pulling a lot of other imports in that are not
# needed.  As importing some of the modules can be quite costly speed-wise,
# the clarity of having the import statements at the beginning is consciously
# compromised.
from __future__ import with_statement

import contextlib
import fnmatch
import inspect
import itertools
import logging
import os
import re
import subprocess
import sys
import warnings
from collections import UserDict


try:
    # should make multiprocessing less stressfull
    import dill as pickle
except ImportError:
    import pickle
import multiprocessing
from queue import Queue
import threading
import hashlib
import functools
import random
import numpy as np
try:
    import numexpr as ne
    NE = True
except ImportError:
    NE = False
# from scipy import optimize, stats
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
##from lhglib.contrib import smoothing
# further imports following below
# import string
# import doctest
# from scipy.stats import stats as sp_stats

# Generic


def _build_arg_str(function, *func_args, **func_kwds):
    """Builds a string that completely describes the parameters in a function
    call. This helps to cache function results that have no side-effects."""
    # remember that default arguments arrive empty in **func_kwds.
    # build dictionary of argument-names to default argument values
    spec_arg_names = inspect.getargspec(function).args
    arg_dict = dict.fromkeys(spec_arg_names, None)
    spec_arg_values = inspect.getargspec(function).defaults
    # spec_arg_values apply to the last n spec_arg_names
    if spec_arg_names and spec_arg_values:
        for name, val in zip(spec_arg_names[::-1],
                             spec_arg_values[::-1]):
            arg_dict[name] = val

    # change the default values according to the passed values
    for arg, arg_name in zip(func_args, spec_arg_names):
        arg_dict[arg_name] = arg
    arg_dict.update(func_kwds)

    return "__".join("%s_%s" % (key, arg_dict[key])
                     for key in sorted(arg_dict.keys()))


def remove_latex_command(command, str_, remove_content=False, regex=False):
    r"""Removes possibly nested latex commands from str_.
    According to this http://stackoverflow.com/a/15864833 this cannot be done
    with regexes (they are stateless and cannot count parentheses).

    >>> str_ = r"\emph{This is \citep{bla}.} And so \emph{on}."
    >>> print remove_latex_command("emph", str_)
    This is \citep{bla}. And so on.
    >>> str_ = r"Keep me. \sout{Delete me!}"
    >>> remove_latex_command(r"sout", str_, remove_content=True)
    'Keep me. '
    """
    if not command.startswith(r"\\"):
        command = r"\\" + command
    if not command.endswith(r"\{"):
        command = command + r"\{"

    while True:
        matches = re.search(command, str_)
        if matches is None:
            break
        match = matches.group(0)
        i = max(matches.start(0), 0)
        opening_pars = 1
        j = matches.end(0)
        while opening_pars > 0:
            if str_[j] == "{":
                opening_pars += 1
            elif str_[j] == "}":
                opening_pars -= 1
            j += 1
        if remove_content:
            str_ = str_[:i] + str_[j:]
        else:
            str_ = str_[:i - 1] + str_[i + len(match) + 1:j - 1] + str_[j:]
    return str_


def asscalar(func):
    """Return the result as a scalar if it has len == 1."""
    @functools.wraps(func)
    def wrapped(*args, **kwds):
        result = np.atleast_1d(func(*args, **kwds))
        return np.asscalar(result) if len(result) == 1 else result
    return wrapped


def pickle_cache(filepath_template="%s.pkl", warn=True):
    """Use this as a function decorator to cache the result of a function as a
    pickle-file. The filename is determined by the arguments in the function.
    If the filename turns out to be too long, a hash of it is used."""
    def function_wrapper(function):
        @functools.wraps(function)
        def pickle_function(*args, **kwds):
            # set a filename based on the arguments passed
            arg_dict_str = sanitize(_build_arg_str(function, *args, **kwds))
            if len(arg_dict_str) > 0:
                filepath = filepath_template % arg_dict_str
            else:
                filepath = filepath_template

            def hash_(filepath):
                name_hash = hashlib.md5(os.path.basename(filepath)).hexdigest()
                return os.path.join(os.path.dirname(filepath), name_hash)

            def read(filepath):
                with open(filepath, "rb") as pi_file:
                    return pickle.load(pi_file)

            if os.path.exists(filepath) or os.path.exists(hash_(filepath)):
                try:
                    if warn:
                        warnings.warn(
                            "I am not executing %s, but restoring the " %
                            repr(function) +
                            "result from its last execution with the " +
                            "same parameters. \nThe result is stored " +
                            "here: %s" % filepath)
                    return read(filepath)
                except IOError:
                    if os.path.exists(hash_(filepath)):
                        return read(hash_(filepath))

            else:
                result = function(*args, **kwds)

                def dump(filepath):
                    with open(filepath, "wb") as pi_file:
                        pickle.dump(result, pi_file)
                try:
                    dump(filepath)
                except IOError:
                    # maybe the filename was too long
                    dump(hash_(filepath))
                return result
        return pickle_function
    return function_wrapper


def mem_cache(function):
    """Use this function decorator to cache the result of a function in memory.
    """
    stored = {}

    @functools.wraps(function)
    def store_restore(*args, **kwds):
        parameter_str = _build_arg_str(function, *args, **kwds)
        try:
            return stored[parameter_str]
        except KeyError:
            result = function(*args, **kwds)
            stored[parameter_str] = result
            return result
    return store_restore


def log_assert(bool_, message="", logger=None, logger_name="", verbose=True):
    """Use this as a replacement for assert if you want the failing of the
    assert statement to be logged."""
    if logger is None:
        logger = logging.getLogger(logger_name)
    try:
        assert bool_, message
    except AssertionError:
        # construct an exception message from the code of the calling frame
        last_stackframe = inspect.stack()[-2]
        source_file, line_no, func = last_stackframe[1:4]
        source = "Traceback (most recent call last):\n" + \
            '  File "%s", line %s, in %s\n    ' % (source_file, line_no, func)
        if verbose:
            # include more lines than that where the statement was made
            source_code = open(source_file).readlines()
            source += "".join(source_code[line_no - 3:line_no + 1])
        else:
            source += last_stackframe[-2][0].strip()
        logger.debug("%s\n%s" % (message, source))
        raise AssertionError("%s\n%s" % (message, source))


def slice_repr(slice_):
    """Returns a string describing a slice-object.

    Examples
    --------
    >>> slice_repr(slice(None))
    ':'
    >>> slice_repr(slice(1, None, 2))
    '1::2'
    """
    if (slice_.start == 0) or (slice_.start is None):
        sl_str = ":"
    else:
        sl_str = "%d:" % slice_.start
    sl_str += "" if slice_.stop is None else str(slice_.stop)
    if (slice_.step is None) or (slice_.step == 1):
        sl_str += ""
    else:
        sl_str += ":%d" % slice_.step
    return sl_str


def item_repr(item):
    """Return a string describing an item (think of "__getitem__").

    Examples
    --------
    >>> item_repr((slice(None), 0, 10))
    ':, 0, 10'
    >>> item_repr(slice(None))
    ':'
    """
    try:
        it_list = [(slice_repr(subit) if type(subit) is slice else str(subit))
                   for subit in item]
    except TypeError:
        try:
            it_list = [slice_repr(item)]
        except AttributeError:
            it_list = [str(item)]

    return ", ".join(it_list)


class ADict(UserDict):
    def __add__(self, other):
        # we need a copy to work with
        left_dict = dict(self)
        left_dict.update(other)
        # make sure we can do this operation also with the returned
        # object
        return ADict(left_dict)

    def __sub__(self, other):
        left_dict = dict(self)
        if isinstance(other, dict):
            del_keys = other.keys()
        elif isinstance(other, str):
            del_keys = other,
        else:
            del_keys = other
        for del_key in del_keys:
            del left_dict[del_key]
        return ADict(left_dict)


class ProgressBar(object):

    """Text animation of a progress bar.
    Shamelessly stolen from ipython who stole it from pymc.
    (docs/examples/notebooks/Animations_and_Progress.ipynb)

    Use it like this:
    >>> import time
    >>> p = ProgressBar(1000)
    >>> for i in range(1001):
    ...    time.sleep(0.002)
    ...    p.animate(i) # doctest: +SKIP
    """

    def __init__(self, iterations):
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 50
        self._update_amount(0)

    def animate(self, iter_):
        print('\r', self, end=' ')
        sys.stdout.flush()
        self._update_iteration(iter_ + 1)
        if iter_ >= self.iterations:
            print

    def _update_iteration(self, elapsed_iter):
        self._update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        self.prog_bar += ('  %d of %s complete' %
                          (elapsed_iter, self.iterations))

    def _update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = ('[' + self.fill_char * num_hashes +
                         ' ' * (all_full - num_hashes) + ']')
        pct_place = (len(self.prog_bar) // 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])

    def __str__(self):
        return str(self.prog_bar)


class Deadend(threading.Thread):

    """This thread-class has only a Queue to get parameters for input and no
    means to give back results.  It can be used to save data, for example.
    """

    def __init__(self, func):
        super(Deadend, self).__init__()
        self.daemon = True
        self.func = func
        self.work_request_queue = Queue()
        self.start()

    def run(self):
        while True:
            args, kwds = self.work_request_queue.get()
            self.func(*args, **kwds)
            self.work_request_queue.task_done()


class Worker(multiprocessing.Process):

    """Use a number of instances of this class to form a pool of workers,
    waiting for functions and parameters to do work in other processes.  Pass
    the same request and result queue to all workers in the initialization
    step.

    More than less stolen from Alex Martelli's excellent "Python in a Nutshell"
    book."""
    request_id = 0

    def __init__(self, request_queue, result_queue):
        super(Worker, self).__init__()
        self.daemon = True
        self.request_queue = request_queue
        self.result_queue = result_queue
        self.start()

    def work(self, func, *args, **kwds):
        Worker.request_id += 1
        self.request_queue.put((Worker.request_id, func, args, kwds))
        return Worker.request_id

    def run(self):
        while True:
            request_id, func, args, kwds = self.request_queue.get()
            # we were told to go home
            if request_id is None:
                self.request_queue.task_done()
                return
            self.result_queue.put((request_id, func(*args, **kwds)))


class WhereWorker(multiprocessing.Process):

    """Does a np.where search."""
    cmp_methods = {"==": "__eq__", "!=": "__ne__",
                   ">=": "__ge__", ">": "__gt__",
                   "<=": "__le__", "<": "__lt__"}

    def __init__(self, request_queue, result_queue, comparison):
        super(WhereWorker, self).__init__()
        # the first working request should later get an id of 0
        self.request_id = -1
        self.daemon = True
        self.request_queue = request_queue
        self.result_queue = result_queue
        self.cmp = WhereWorker.cmp_methods[comparison]
        assert comparison in WhereWorker.cmp_methods.keys(), \
            "comparison must be one of '%s'" % \
            ", ".join(WhereWorker.cmp_methods.keys())
        self.start()

    def work(self, values1, values2):
        """values1 and values2 are expected to be 1-dim arrays."""
        self.request_id += 1
        self.request_queue.put((self.request_id, values1, values2))

    def go_home(self):
        """Signifies self.run to end its loop."""
        self.request_queue.put((None, None, None))

    def run(self):
        while True:
            request_id, values1, values2 = self.request_queue.get()
            if request_id is None:
                # meaning we were told to go home
                self.request_queue.task_done()
                return
            val1_cmp = getattr(values1, self.cmp)
            try:
                indices = np.where(val1_cmp(values2[:, np.newaxis]))[1]
            except (TypeError, IndexError):
                result = np.where(val1_cmp(values2))
                try:
                    indices = result[0]
                except IndexError:
                    indices = np.array([], dtype="int")
            self.result_queue.put((request_id, indices))
            self.request_queue.task_done()


def kwds_from_locals(frame=1, exclude=(None,)):
    """Nice to avoid boilerplate code when defining functions that more or less
    just define parameters for a common lower-level function.

    Attention: the "**" argument in the calling frame's signature must be
    called "**kwds"!  That might be overcome by using the inspect module...
    """
    kwds = sys._getframe(frame).f_locals
    # merge **-dictionary with kwds to avoid nested kwds
    if "kwds" in kwds and isinstance(kwds["kwds"], dict):
        kwds.update(kwds["kwds"])
        del kwds["kwds"]
    # delete items that are in 'exclude'
    for key in kwds.keys():
        if key in exclude:
            del kwds[key]
    if "self" in kwds:
        del kwds["self"]
    return kwds


def attrs_from_locals(instance, exclude=(None,)):
    """Stolen and shortened from http://code.activestate.com/recipes/286185/
    Sets every local variable mentioned so far as an instance attribute.

    This breeds very implicit __init__-methods.  But "Explicit is better than
    implicit" my ass.  As if the code of "this.py" (where the Zen of Python is
    stored) would be in any way explicit..."""
    for key, value in kwds_from_locals(frame=2, exclude=exclude).items():
        setattr(instance, key, value)


def cache(*names, **name_values):
    """Use as a decorator, to supply *names attributes that can be used as
    a cache. The attributes are set to None during compile time. The
    wrapped function also has a 'clear_cache'-method to delete those
    variables.

    Parameter
    ---------
    *names : str
    """
    def wrapper(function):
        @functools.wraps(function)
        def cache_holder(*args, **kwds):
            return function(*args, **kwds)
        cache_holder._cache_names = names
        cache_holder._cache_name_values = name_values
        cache_holder.clear_cache = lambda: clear_def_cache(cache_holder)
        cache_holder.clear_cache()
        return cache_holder
    return wrapper


def clear_def_cache(function, cache_names=None, cache_name_values=None):
    """I often use a simplified function cache in the form of
    'function.attribute = value'.  This function helps cleaning it up,
    i.e. setting them to None.

    Parameter
    ---------
    function : object with settable attributes
    cache_names : sequence of str or None, optional
        if None, function should have an attribute called _cache_names with
        names of attributes that are cached.
    """
    if cache_names is None:
        cache_names = function._cache_names
    if cache_name_values is None:
        cache_name_values = function._cache_name_values
    for name in cache_names:
        setattr(function, name, None)
    for name, value in cache_name_values.items():
        setattr(function, name, value)


def flatten(sequence, dict_cont="values"):
    """With dict_cont set to "values", this returns the values from each
    dictionary.  Can also be set to "keys" or "items".

    Recipe 4.6: Flattening a Nested Sequence from the Python Cookbook p. 157.
    Expanded to flatten dictionaries also.
    """
    for item in sequence:
        if isinstance(item, dict):
            item = getattr(item, dict_cont)()
        if isinstance(item, (list, tuple)):
            for subitem in flatten(item, dict_cont):
                yield subitem
        else:
            yield item


# Filesystem

@contextlib.contextmanager
def chdir(dirname):
    """Temporarily change the working directory with a with-statement."""
    old_dir = os.path.abspath(os.path.curdir)
    if dirname:  # could be an empty string
        os.chdir(dirname)
    yield
    os.chdir(old_dir)


def sanitize(filename):
    """Sanitize a filename so it can be used safely on a unix-system.
    Probably needs some more work."""
    import string
    identity = string.maketrans('', '')
    bad_chars = string.punctuation
    allowed_punctuation = ('_', '.', '-')
    for punct in allowed_punctuation:
        bad_chars = bad_chars.replace(punct, '')
    filename = filename.translate(identity, bad_chars)
    return filename.replace(' ', '_')


def assemble_path(*args):
    """Concatenate args into a filepath with appropriate slashes.  Elements of
    args can be iterables, except the first one.  (so slightly different to
    os.path.join)
    Deprecated but kept for nELCOM (not sure if it is needed in this version)
    """
    path = [args[0]]
    for arg in flatten(args[1:]):
        if not path[-1].endswith(os.sep):
            path[-1] += os.sep
        while arg.startswith(os.sep):
            arg = arg.lstrip(os.sep)
        path += arg
    return "".join(path)


def assemble_path_(*args):
    """Concatenate args into a filepath with appropriate slashes.  Elements of
    args can be (nested) iterables.  (so slightly different to os.path.join)
    """
    return os.path.join(*flatten(args))


def first_existence(paths, file_=""):
    """Returns first path from paths that exists in the filesystem. If file_ is
    given, it is appended to every path."""
    for path in paths:
        path = os.path.join(path, file_)
        if os.path.exists(path):
            return path
    raise (IOError,
           "No filepath found: %s" % ("%s%s, " % (os.sep, file_)).join(paths))


def recursive_glob(treeroot, pattern=None):
    """Look recursively for files in treeroot matching the given pattern.

    Taken from
    http://stackoverflow.com/questions/2186525/
    use-a-glob-to-find-files-recursively-in-python
    """
    if pattern is None:
        treeroot, pattern = (os.path.dirname(treeroot),
                             os.path.basename(treeroot))
    results = []
    for base, _, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results


def mkdir2(directory, root=""):
    """ Use mkdirs instead of this function!
    Recursively creates the empty directories specified as directory.
    """
    dirs = directory.split(os.sep)
    current_dir = assemble_path(root, dirs[0])
    if not os.path.exists(current_dir):
        os.mkdir(current_dir)
    root = current_dir
    if len(dirs[1:]) > 0:
        mkdir2(os.sep.join(dirs[1:]), root)


def cpu_of_pid(pid):
    """cpu usage of a process. Unix-specific.

    Parameters
    ----------
    pid : int
        pid of the process

    Returns
    -------
    cpu : float
        cpu usage as given by ps. Or None if not available.
    """
    ps = subprocess.Popen(["ps", "-p", str(pid), "-o", "%cpu"],
                          stdout=subprocess.PIPE)
    call_str = "".join(ps.stdout)
    if call_str:
        try:
            return float(call_str.split()[1])
        except ValueError:
            return


# Numeric


def nanavg(x, axis=None, ddof=0):
    ii = np.isfinite(x)
    return (np.nansum(x, axis=axis) /
            (np.sum(ii, axis=axis) - ddof))
# return (np.sum(x[ii].reshape(x.shape), axis=axis) /
# (np.sum(ii, axis=axis) - ddof))


def nanavg_weighted(x, axis=None, weights=None):
    if weights is None:
        weights = np.ones_like(x)
    ii = np.isfinite(x)
    weights__ = np.zeros_like(x)
    weights__[ii] = weights[ii]
    return (np.nansum(x * weights, axis=axis) /
            (np.sum(weights__, axis=axis)))


# from the newest scipy.integrate
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


##def aggregation(values, agg_func=np.var, max_aggregation=None):
##    """Compute agg_func of all aggregation levels from 1 to max_aggregation."""
##    if max_aggregation is None:
##        max_aggregation = len(values) / 16
##    return np.array([agg_func(smoothing.smooth(values, dt, np.ones, True))
##                     # sumup(values, dt) / dt)
##                     for dt in range(1, max_aggregation)])


def aggregate(values, group_size=2):
    """Coarsen the data in "values" by averaging over "group_size" elements.
    "values" must be 1-dim.  The returned array will have the same length as
    "values".

    Examples
    --------
    >>> a = np.arange(5)
    >>> a; aggregate(a)
    array([0, 1, 2, 3, 4])
    array([ 0.5,  0.5,  2.5,  2.5,  4. ])"""
    n_rows = len(values) // group_size
    cut_here = n_rows * group_size
    temp = np.copy(values[:cut_here])
    averages = temp.reshape((n_rows, group_size)).mean(axis=1)
    front = averages.repeat(group_size)

    back = values[cut_here:].mean().repeat(len(values) - cut_here)
    return np.r_[front, back]


def coarsen_2dim(values):
    """Make a smaller 2-dimensional array out of a bigger one by averaging.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(4*4).reshape((4, 4))
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> coarsen_2dim(a)
    array([[  2.5,   4.5],
           [ 10.5,  12.5]])
    """
    # aggregate along rows
    values = values.astype(float)
    values = (values[:-1] + values[1:])[::2]
    # aggregate along columns
    return ((values[:, :-1] + values[:, 1:]) / 4)[:, ::2]


def biggest_n(values, n_biggest=10):
    """Return the indices of the "n_biggest" values in the n-dimensional
    "values" array.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(20, 10, -1)
    >>> biggest_n(a, 3); biggest_n(a.reshape((5,2)), 1)
    [0, 1, 2]
    (array([0]), array([0]))
    >>> a[biggest_n(a, 3)]
    array([20, 19, 18])
    """
    if n_biggest >= values.size:
        raise IndexError("n_biggest is bigger than values.")
    biggest_value_indices = np.argsort(values.ravel())[:-n_biggest - 1:-1]
    if np.ndim(values) == 1:
        return list(biggest_value_indices)
    else:
        return np.unravel_index(biggest_value_indices, values.shape)


def trim(values, n_remove=2):
    """Scipy makes me angry. The stats submodule has lots of trimming weapons
    making this here look like a toothpick.
    Remove the n_remove smallest and biggest values from the 1-dim array
    values.
    If n_remove is a float between 0 and 1, the upper and lower
    n_remove-quantile of values is removed.

    Examples
    --------
    >>> import numpy as np
    >>> trim(np.arange(10))
    array([2, 3, 4, 5, 6, 7])
    >>> trim(np.arange(10), .45)
    array([4, 5])"""
    if 0 < n_remove < 1:
        n_remove *= len(values)
    return values[np.argsort(values)[n_remove:-n_remove]]


def rotate(sequence):
    """Simple cyclic permutation by shifting the sequence by one element."""
    sequence = list(sequence)
    return [sequence[-1]] + sequence[:-1]


def all_rotations(sequence, rotations=None):
    """Returns a nested list of all possible cyclic rotations of sequence.
    If an int is given for "rotations", only this many rotations are returned.

    Examples
    --------
    >>> all_rotations(range(4))
    [[0, 1, 2, 3], [3, 0, 1, 2], [2, 3, 0, 1], [1, 2, 3, 0]]
    """
    if rotations is None:
        rotations = [list(sequence)]
    if len(rotations) < len(sequence):
        rotations.append(rotate(rotations[-1]))
        return all_rotations(sequence, rotations)
    else:
        return rotations


def gaps(data):
    """Return indices referring to start and end points of gaps (marked by nans
    in the given array 'data'

    Parameters
    ----------
    data : 1dim ndarray, dtype float or bool

    >>> import numpy as np
    >>> a = np.arange(20.)
    >>> a[-1] = np.nan
    >>> gaps(a)
    array([[19, 19]])
    >>> a = np.arange(20.)
    >>> a[[0, 3, 4, 5, 12, 13, -1]] = np.nan
    >>> gaps(a)
    array([[ 0,  0],
           [ 3,  5],
           [12, 13],
           [19, 19]])
    >>> a = np.arange(20.)
    >>> a[[0, 1, 3, 4, 5, 12, -2, -1]] = np.nan
    >>> gaps(a)
    array([[ 0,  1],
           [ 3,  5],
           [12, 12],
           [18, 19]])
    """
    if data.dtype == bool:
        mask = data
    else:
        mask = np.isnan(data)
    if np.all(~mask):
        return []
    diff = np.diff(mask.astype(int))
    begin_ii = (np.where(diff == 1)[0] + 1).tolist()
    end_ii = np.where(diff == -1)[0].tolist()
    if mask[0]:
        if not end_ii[0] < begin_ii[0]:
            end_ii = [0] + end_ii
        begin_ii = [0] + begin_ii
    if (begin_ii[-1] and not end_ii) or begin_ii[-1] > end_ii[-1]:
        end_ii += [len(mask) - 1]

    return np.array([begin_ii, end_ii]).T


def split_to_classes(values, classes, indicators=None):
    """Split values into a list of arrays according to classes.
    Classes must be given in a monotonously increasing form (like bins in
    np.histogram).  The returned list will be one element smaller than classes
    (the elements of which are interpreted as boundaries).
    If indicators are given, values is split according to them.

    Examples
    --------
    >>> values = np.arange(10)
    >>> classes = np.arange(0, 12, 3)
    >>> split_to_classes(values, classes)
    [array([0, 1, 2]), array([3, 4, 5]), array([6, 7, 8])]
    >>> indicators = np.arange(0, 5, .5)
    >>> split_to_classes(values, classes, indicators)
    [array([0, 1, 2, 3, 4, 5]), array([6, 7, 8, 9]), array([], dtype=int64)]
    """
    if indicators is None:
        indicators = np.array(values)

    split_values = []
    for left, right in zip(classes[:-1], classes[1:]):
        indices = np.where((indicators >= left) & (indicators < right))
        if len(indices) > 0:
            split_values += [values[indices]]
        else:
            split_values += [np.array([])]
    return split_values


def csv2array(filename, startfrom=None, delimiter=None, conversion=float):
    """Return an array of a csv-file.  Do not use: numpy.loadtxt() can do more
    and is probably faster."""
    with open(filename) as csv_file:
        return np.array([[conversion(value) for value in line.split(delimiter)]
                         for line in csv_file.readlines()[startfrom:]])


def list_transpose(list_):
    """Transposes a "2-dim" nested list.

    Examples
    --------
    >>> list_transpose([[1, 2, 3], [4, 5, 6]])
    [[1, 4], [2, 5], [3, 6]]
    """
    return map(list, zip(*list_))


def csv2list(filename, startfrom=None, delimiter=None, column_ids=None,
             conversions=None, comment="#"):
    """Returns a list of each column of a csv-file."""
    if conversions is None:
        # no conversion corresponds to a string-conversion.  itertools.repeat
        # gives us those for as many columns that might be there.
        conversions = itertools.repeat(str)
    if ((len(np.atleast_1d(column_ids)) > 1) and
            (len(np.atleast_1d(conversions)) == 1)):
        # as convenience, this expands the conversions to the length of the
        # given column_ids
        column_conversions = conversions
        conversions = itertools.repeat(conversions)

    with open(filename) as csv_file:
        all_data = [[conversion(value.strip()) for value, conversion
                     in zip(line.split(delimiter), conversions)]
                    for line in itertools.islice(csv_file, startfrom)
                    if not line.lstrip().startswith(comment)]

    # "transpose" rows to columns
    columns = list_transpose(all_data)

    if column_ids is None:
        return columns
    elif len(column_ids) == 1:
        # do not return a nested list if there is only one column
        return [column_conversions[0](value)
                for value in columns[column_ids[0]]]
    else:
        return [[conversion(value) for value in columns[ii]]
                for ii, conversion in zip(column_ids, column_conversions)]


def csv2arrays(filename, *args, **kwds):
    return (np.array(a) for a in csv2list(filename, *args, **kwds))


def csv2dict(filename, *args, **kwds):
    """Returns a dictionary containing the columns of a csv-file.  The keys
    are taken from the first row of the file."""
    aslist = csv2list(filename, *args, **kwds)
    return {column[0].strip(): column[1:] for column in aslist}


def last_lines(filename, n_lines):
    """Returns the last `n_lines` from `filename`.

    Parameter
    ---------
    filename : str
    n_lines : int

    Notes
    -----
    This is stolen from
    http://stackoverflow.com/questions/136168/
    get-last-n-lines-of-a-file-with-python-similar-to-tail.

    """
    with open(filename, "r") as file_:
        line = file_.readline()
        total_lines_wanted = n_lines
        linesep = line[len(line.rstrip()):]

        BLOCK_SIZE = 1024
        file_.seek(0, 2)
        block_end_byte = file_.tell()
        lines_to_go = total_lines_wanted
        block_number = -1
        # blocks of size BLOCK_SIZE, in reverse order starting from the
        # end of the file
        blocks = []
        while lines_to_go > 0 and block_end_byte > 0:
            if (block_end_byte - BLOCK_SIZE > 0):
                # read the last block we haven't yet read
                file_.seek(block_number * BLOCK_SIZE, 2)
                blocks.append(file_.read(BLOCK_SIZE))
            else:
                # file too small, start from begining
                file_.seek(0, 0)
                # only read what was not read
                blocks.append(file_.read(block_end_byte))
            lines_found = blocks[-1].count(linesep)
            lines_to_go -= lines_found
            block_end_byte -= BLOCK_SIZE
            block_number -= 1

    all_read_text = ''.join(reversed(blocks))
    lines = linesep.join(all_read_text.splitlines()[-total_lines_wanted:])
    return lines


def hard_calc(m_array, filepath, operation, chunk_size, *o_args, **o_kwds):
    """Use this for calculations on huge arrays that won't fit into memory.
    (think of the size of the array as the amount of schnapps you drank friday
    night and the memory as, well, your memory of what happened that night).

    Parameters
    ----------
    m_array :    A memmap object.
    filepath :   The filepath to the memmap object.
    operation :  A function used to assign values to "m_array".
    chunk_size : Size of the part of "m_array" that is hold in memory in Bytes.
                 If None, it is set to 512MB.
    *o_args :    Indexable parameters to "operation".  If omitted, "operation"
                 is called with "m_array".
    **o_kwds :   Keyword arguments passed on to "operation".
    """
    o_args = [m_array] if len(o_args) == 0 else o_args
    chunk_size = 512 * 1024 ** 2 if chunk_size is None else chunk_size
    row_size = np.prod(m_array.shape[1:]) * m_array.dtype.itemsize
    step_length = int(chunk_size / row_size) if chunk_size > row_size else 1
    # needed to be able to reopen m_array
    m_dtype, m_shape = m_array.dtype, m_array.shape

    ii = 0
    while ii is not None:
        ii_new = ii + step_length if ii + step_length < len(m_array) else None
        sliced_o_args = [o_arg[ii:ii_new] for o_arg in o_args]
        m_array[ii:ii_new] = operation(*sliced_o_args, **o_kwds)
        del m_array
        m_array = np.memmap(filepath, mode='r+', dtype=m_dtype, shape=m_shape)
        ii = ii_new
    return m_array


class HardCalc(object):

    def __init__(self, filepath, m_shape, m_dtype='float64',
                 chunk_size=512 * 1024 ** 2):
        """Use this for calculations on huge arrays that won't fit into memory.
        (think of the size of the array as the amount of schnapps you drank
        friday night and the memory as, well, your memory of what happened that
        night).

        It makes use of the numpy.memmap-class and does calculations
        chunk-wise. "chunk_size" determines how much Bytes of the memmap-array
        are hold in memory.
        """
        m_array = np.memmap(filepath, mode='w+', dtype=m_dtype, shape=m_shape)
        row_size = np.prod(m_array.shape[1:]) * m_array.dtype.itemsize
        step_length = \
            int(chunk_size / row_size) if chunk_size > row_size else 1
        attrs_from_locals(self)

    @staticmethod
    def operation():
        raise AttributeError("Append your own operation-method, otherwise I "
                             "have nothing to do.")

    def __call__(self, *o_args, **o_kwds):
        """Applies "operation". Make sure that method is present.
        Called without "o_args" the memmap-array is used as a parameter for
        "operation".
        """
        o_args = [self.m_array] if len(o_args) == 0 else o_args
        ii = 0
        while ii is not None:
            ii_new = ii + self.step_length if \
                ii + self.step_length < len(self.m_array) else None
            sliced_o_args = [o_arg[ii:ii_new] for o_arg in o_args]
            self.m_array[ii:ii_new] = self.operation(*sliced_o_args, **o_kwds)
            del self.m_array  # writes to file and frees memory
            self.m_array = np.memmap(self.filepath, mode='r+',
                                     dtype=self.m_dtype, shape=self.m_shape)
            ii = ii_new
        return self.m_array


def memmap_cache(filepath, m_shape, generating_func, transform=None,
                 *g_args, **g_kwds):
    """Returns the result of "generating_func(*g_args, **g_kwds)" and stores
    it as a memmap-file in filepath.  If the filepath allready exists, it
    loads the memmap-object and returns it.

    This is also an example on how to use the HardCalc class.
    """
    if transform is None:
        transform = lambda x: x

    if os.path.exists(filepath):
        try:
            return transform(np.memmap(filepath, dtype=float, mode="c",
                                       shape=m_shape))
        except ValueError:
            print("Memmap file exists but is not loadable. " \
                "Will rebuild it now.")
            os.remove(filepath)
            return memmap_cache(filepath, m_shape, generating_func, transform,
                                *g_args, **g_kwds)
    else:
        print("Generating memmap-file...")
        Hc = HardCalc(filepath, m_shape)
        Hc.operation = generating_func
        return transform(Hc(*g_args, **g_kwds))


def get_stats(values):
    """Some descriptive statistical values for 1-dim data.
    Pretty inefficient, since there must be some kind of redundant calculation
    of intermediate results.
    """
    from scipy.stats import stats as sp_stats
    values = np.array(values)
    stats = {
        "mode": sp_stats.mode(values),
        "median": np.median(values),
        "Q_25": sp_stats.scoreatpercentile(values, 25),
        "Q_75": sp_stats.scoreatpercentile(values, 75),
        "std": np.std(values)
    }
    stats["q-spread"] = stats["Q_75"] - stats["Q_25"]
    stats["N"], (stats["min"], stats["max"]), stats["mean"], \
        stats["var"], stats["skew"], stats["kurtosis"] = \
        sp_stats.describe(values)
    return stats


# Plotting


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
legend_subtitle = LegendSubtitleHandler()


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
        print('Caution: you get more ev. points than input data\
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


@cache(h_max=-np.inf)
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


if __name__ == "__main__":
    str_ = r"Keep me. \sout{Delete me!}"
    remove_latex_command(r"sout", str_, remove_content=True)

    import doctest
    doctest.testmod()

    fig, ax = plt.subplots()
    line, = ax.plot(np.arange(10))
    ax.legend([line, None], ("line", "find me"),
              handler_map={None, LegendSubtitleHandler()})
    plt.show()
