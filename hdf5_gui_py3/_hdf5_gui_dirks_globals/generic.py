"""Dirks globals: generic."""

from ._shared import *


__all__ = ['_build_arg_str', 'remove_latex_command', 'asscalar', 'pickle_cache', 'mem_cache', 'log_assert', 'slice_repr', 'item_repr', 'ADict', 'ProgressBar', 'Deadend', 'Worker', 'WhereWorker', 'kwds_from_locals', 'attrs_from_locals', 'cache', 'clear_def_cache', 'flatten']


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
    """Removes possibly nested latex commands from str_.
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
    if (slice_.start is 0) or (slice_.start is None):
        sl_str = ":"
    else:
        sl_str = "%d:" % slice_.start
    sl_str += "" if slice_.stop is None else str(slice_.stop)
    if (slice_.step is None) or (slice_.step is 1):
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
        print('\r', self),
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
        self.work_request_queue = Queue.Queue()
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

