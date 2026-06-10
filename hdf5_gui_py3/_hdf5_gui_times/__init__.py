"""Internal package for the split times.py implementation."""

from importlib import import_module

from . import _shared


PART_MODULES = ['cwr', 'datetime_conversions', 'string_conversions', 'timestamps', 'series', 'periodic']


def load_namespace():
    modules = [import_module(f"{__name__}.{module_name}") for module_name in PART_MODULES]
    namespace = {
        name: value
        for name, value in vars(_shared).items()
        if not name.startswith("__")
    }
    for module in modules:
        for name in module.__all__:
            namespace[name] = getattr(module, name)
    for module in modules:
        module.__dict__.update(namespace)
    return namespace, tuple(namespace)
