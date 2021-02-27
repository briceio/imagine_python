# extensions.py
#
# Copyright 2021 Brice MARTIN
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import threading
from gi.repository import GLib
from time import sleep
import cairo
from PIL import Image

__all__ = ['delay', 'threaded', 'cario_image_from_pil', 'pil_from_cairo_surface', 'normalize_rect']

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

def pil_from_cairo_surface(surface, format='RGB'):
    image = Image.frombuffer(mode = 'RGBA', size = (surface.get_width(), surface.get_height()), data = surface.get_data(),)
    b, g, r, a = image.split()
    return Image.merge('RGBA', (r, g, b, a)) if format=='RGBA' else Image.merge('RGB', (r, g, b))

def cario_image_from_pil(im, alpha=1.0, format=cairo.FORMAT_ARGB32):
    assert format in (cairo.FORMAT_RGB24, cairo.FORMAT_ARGB32), "Unsupported pixel format: %s" % format
    if 'A' not in im.getbands():
        im.putalpha(int(alpha * 256.))
    arr = bytearray(im.tobytes('raw', 'BGRa'))
    surface = cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)
    return surface


def normalize_rect(x1, y1, x2, y2):
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), (abs(x2 - x1) > 0 and abs(y2 - y1) > 0)

