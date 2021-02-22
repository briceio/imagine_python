import threading
from gi.repository import GLib
from time import sleep

__all__ = ['delay']

def delay(delay, main_thread=True):
    def wrapper(f):
        def run(*args, **kwargs):
            def t(data):
                f, args, kwargs, delay, main_thread = data
                sleep(delay) # delay the call
                if main_thread:
                    GLib.idle_add(lambda: f(*args, **kwargs))
                else:
                    f(*args, **kwargs)

            data = f, args, kwargs, delay, main_thread
            thread = threading.Thread(target=t, args=(data,))
            thread.start()
        return run
    return wrapper

