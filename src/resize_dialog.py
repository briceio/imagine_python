from gi.repository import Gtk
from gi.repository import GdkPixbuf
import cairo
import math
from io import BytesIO
from PIL import Image

@Gtk.Template(resource_path='/io/boite/imagine/resize_dialog.ui')
class ResizeDialog(Gtk.Dialog):
    __gtype_name__ = 'ResizeDialog'

    width_spinbutton: Gtk.SpinButton = Gtk.Template.Child("resize_dialog_width_spinbutton")
    height_spinbutton: Gtk.SpinButton = Gtk.Template.Child("resize_dialog_height_spinbutton")
    keep_aspect_ratio_checkbox: Gtk.CheckButton = Gtk.Template.Child("resize_dialog_keep_aspect_ratio_checkbox")


    def __init__(self, width, height, **kwargs):
        super().__init__(**kwargs)

        self.width = width
        self.height = height
        self._ratio = width / height
        self._sync = False

        self.width_spinbutton.set_range(0, 10000)
        self.width_spinbutton.set_increments(1.0, 10.0)
        self.width_spinbutton.set_value(self.width)
        self.width_spinbutton.connect("value-changed", self.sync_size)

        self.height_spinbutton.set_range(0, 10000)
        self.height_spinbutton.set_increments(1.0, 10.0)
        self.height_spinbutton.set_value(self.height)
        self.height_spinbutton.connect("value-changed", self.sync_size)

        self.keep_aspect_ratio_checkbox.connect("toggled", self.sync_size)

    def sync_size(self, widget):
        if self._sync:
            return

        self._sync = True
        width = self.width
        height = self.height

        if self.keep_aspect_ratio_checkbox.get_active():
            if widget == self.height_spinbutton and self.height_spinbutton.get_value() != height:
                height = self.height_spinbutton.get_value()
                width = height * self._ratio
                self.width_spinbutton.set_value(width)
            elif self.width_spinbutton.get_value() != width:
                width = self.width_spinbutton.get_value()
                height = width / self._ratio
                self.height_spinbutton.set_value(height)
        else:
            width = self.width_spinbutton.get_value()
            height = self.height_spinbutton.get_value()

        self.width = width
        self.height = height

        self._sync = False
