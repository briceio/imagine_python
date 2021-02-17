from gi.repository import Gtk
from gi.repository import GdkPixbuf
import cairo
import math
from io import BytesIO
from PIL import Image

@Gtk.Template(resource_path='/io/boite/imagine/resize_dialog.ui')
class ResizeDialog(Gtk.Dialog):
    __gtype_name__ = 'ResizeDialog'

    _width_spinbutton = Gtk.Template.Child("resize_dialog_width_spinbutton")
    _height_spinbutton = Gtk.Template.Child("resize_dialog_height_spinbutton")

    def __init__(self, width, height, **kwargs):
        super().__init__(**kwargs)

        self.width = width
        self.height = height

        self._width_spinbutton.set_range(0, 10000)
        self._width_spinbutton.set_increments(1.0, 10.0)
        self._width_spinbutton.set_value(self.width)
        self._width_spinbutton.connect("value-changed", self.sync_size)

        self._height_spinbutton.set_range(0, 10000)
        self._height_spinbutton.set_increments(1.0, 10.0)
        self._height_spinbutton.set_value(self.height)
        self._height_spinbutton.connect("value-changed", self.sync_size)

    def sync_size(self, button):
        self.width = self._width_spinbutton.get_value()
        self.height = self._height_spinbutton.get_value()
