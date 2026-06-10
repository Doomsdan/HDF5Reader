"""Dirks globals: files."""

from ._shared import *


__all__ = ['chdir', 'sanitize', 'assemble_path', 'assemble_path_', 'first_existence', 'recursive_glob', 'mkdir2', 'cpu_of_pid']


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

