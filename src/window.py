# window.py
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

from .resize_dialog import ResizeDialog

from gi.repository import Gtk
from gi.repository import GdkPixbuf
import cairo
import math
from io import BytesIO
from PIL import Image

@Gtk.Template(resource_path='/io/boite/imagine/window.ui')
class ImagineWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ImagineWindow'

    # scale factor
    scale = 1.0

    # widgets
    drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    zoom_spinbutton: Gtk.SpinButton = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # DEBUG load test image
        self.load_image("/home/brice/Données/Temp/pic.jpg")

        # zoom
        self.zoom_spinbutton.set_range(0.1, 10.0)
        self.zoom_spinbutton.set_increments(0.1, 1.0)
        self.zoom_spinbutton.set_value(1.0)

        # binding
        self.drawing_area.connect("draw", self.on_draw)

        # center window
        self.set_size_request(1024, 768)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

    def load_image(self, image):
        im = Image.open(image)
        buffer = BytesIO()
        im.save(buffer, format="PNG")
        buffer.seek(0)

        # create cairo surface
        self.image = cairo.ImageSurface.create_from_png(buffer)

    def save(self):
        # TODO surface.write_to_png
        pass

    @Gtk.Template.Callback("on_file_open")
    def on_file_open(self, widget):
        dialog = Gtk.FileChooserDialog("Image to open", self, Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.set_name("Images")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        dialog.add_filter(filter)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            print("ok")

        dialog.destroy()

    @Gtk.Template.Callback("on_zoom_changed")
    def on_zoom_changed(self, widget):
        self.scale = self.zoom_spinbutton.get_value()
        self.redraw_image()

    @Gtk.Template.Callback("on_resize")
    def on_resize(self, widget):
        dialog = ResizeDialog()
        dialog.set_transient_for(self) # link dialog to parent
        dialog.show_all()
        pass

    @Gtk.Template.Callback("on_crop")
    def on_crop(self, widget):
        print("crop")

    def redraw_image(self):
        self.drawing_area.queue_draw()

    def on_draw(self, w, cr):

        # scale
        self.drawing_area.set_size_request(self.scale * self.image.get_width(), self.scale * self.image.get_height())
        cr.scale(self.scale, self.scale)

        cr.set_source_surface(self.image, 0, 0)
        cr.paint()

        # line
        cr.set_source_rgb(1, 0, 0)
        cr.set_line_width(2)
        cr.move_to(0, 0)
        cr.line_to(100, 100)
        cr.stroke()

        # text
        cr.set_source_rgb(1, 1, 0)
        cr.select_font_face("Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(40)
        cr.move_to(40, 40)
        cr.show_text("This is a test")

