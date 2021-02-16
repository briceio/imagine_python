from gi.repository import Gtk
from gi.repository import GdkPixbuf
import cairo
import math
from io import BytesIO
from PIL import Image

@Gtk.Template(resource_path='/io/boite/imagine/resize_dialog.ui')
class ResizeDialog(Gtk.Dialog):
    __gtype_name__ = 'ResizeDialog'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
