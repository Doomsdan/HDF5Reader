"""Dirks globals: calc cache."""

from ._shared import *


__all__ = ['hard_calc', 'HardCalc', 'memmap_cache', 'get_stats']


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

