import threading
from gi.repository import GLib
from time import sleep
import cairo

__all__ = ['delay', 'threaded', 'cario_image_from_pil']

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

def threaded():
    def wrapper(f):
        def run(*args, **kwargs):
            def t(data):
                f, args, kwargs = data
                f(*args, **kwargs)

            data = f, args, kwargs
            thread = threading.Thread(target=t, args=(data,))
            thread.start()
        return run
    return wrapper

def cario_image_from_pil(im, alpha=1.0, format=cairo.FORMAT_ARGB32):
    """
    :param im: Pillow Image
    :param alpha: 0..1 alpha to add to non-alpha images
    :param format: Pixel format for output surface
    """
    assert format in (cairo.FORMAT_RGB24, cairo.FORMAT_ARGB32), "Unsupported pixel format: %s" % format
    if 'A' not in im.getbands():
        im.putalpha(int(alpha * 256.))
    arr = bytearray(im.tobytes('raw', 'BGRa'))
    surface = cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)
    return surface
