import threading
from gi.repository import GLib
from time import sleep

__all__ = ['delay']

def delay(delay):
    def wrapper(f):
        def run(*args, **kwargs):
            def t(data):
                f, args, kwargs, delay = data
                sleep(delay)
                GLib.idle_add(lambda: f(*args, **kwargs))

            data = f, args, kwargs, delay
            thread = threading.Thread(target=t, args=(data,))
            thread.start()
        return run
    return wrapper

