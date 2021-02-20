import threading
import traceback
from gi.repository import GLib
from time import sleep
from functools import wraps

__all__ = ['unsync', 'delayed']

def _async_call(f, args, kwargs, on_done):
    def run(data):
        f, args, kwargs, on_done = data
        error = None
        result = None
        try:
            result = f(*args, **kwargs)
        except Exception as e:
            e.traceback = traceback.format_exc()
            error = 'Unhandled exception in async call:\n{}'.format(e.traceback)
        if on_done != None:
            GLib.idle_add(lambda: on_done(result, error))

    data = f, args, kwargs, on_done
    thread = threading.Thread(target=run, args=(data,))
    #thread.daemon = True
    thread.start()

def unsync(f, on_done=None):
    def run(*args, **kwargs):
        _async_call(f, args, kwargs, on_done)
    return run

def delayed(delay):
    def wrapper(f):
        def run(*args, **kwargs):
            def run(data):
                f, args, kwargs, delay = data
                sleep(delay)
                GLib.idle_add(lambda: f(*args, **kwargs))

            data = f, args, kwargs, delay
            thread = threading.Thread(target=run, args=(data,))
            thread.start()
        return run
    return wrapper

