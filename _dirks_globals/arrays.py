"""Dirks globals: arrays."""

from ._shared import *


__all__ = ['aggregate', 'coarsen_2dim', 'biggest_n', 'trim', 'rotate', 'all_rotations', 'gaps', 'split_to_classes', 'csv2array', 'list_transpose', 'csv2list', 'csv2arrays', 'csv2dict', 'last_lines']


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

