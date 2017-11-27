

import sys
import inspect
from contextlib import contextmanager

try:
    import maya.cmds as cmds
    MAYA = True
except ImportError:
    MAYA = False

from._handler import BaseHandler, VerboseExceptionHandler

__all__ = ['init', 'pause']

__SYS_HOOK = None
__MANAGER = None


def init():
    global __MANAGER
    print('replaced std')
    __MANAGER = UnhandledExceptionManager({'handlers': [VerboseExceptionHandler]})
    replaceHook(__MANAGER)


def replaceHook(func):
    if MAYA:
        utils = sys.modules['maya.utils']
        utils._guiExceptHook = func
    else:
        sys.excepthook = func


def revert():
    if MAYA:
        utils = sys.modules['maya.utils']
        utils._guiExceptHook = utils.formatGuiException
    else:
        sys.excepthook = sys.__excepthook__


@contextmanager
def pause():
    tmp = sys.excepthook
    sys.excepthook = sys.__excepthook__

    yield

    replaceHook(tmp)


class UnhandledExceptionManager(object):
    def __init__(self, conf):
        self._handlers = []

        for handler in conf.get('handlers', []):
            if isinstance(handler, basestring):
                obj = __import__(handler)()
            elif inspect.isclass(handler) and issubclass(handler, BaseHandler):
                obj = handler()
            elif isinstance(handler, BaseHandler):
                obj = handler
            else:
                raise NotImplementedError

            self._handlers.append(obj)

    def __call__(self, exc_type, exc_value, exc_traceback, detail=2):
        for handler in self._handlers:
            if handler.test(exc_type, exc_value, exc_traceback):
                errstring = handler.handle(exc_type, exc_value, exc_traceback)
                if errstring:
                    sys.stdout.write(errstring)
                    sys.stdout.flush()
