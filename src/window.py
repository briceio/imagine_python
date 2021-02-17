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
from .tools import Tool, AreaSelector

from gi.repository import Gtk
from gi.repository import Gdk
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

    # current tool
    tool: Tool = None

    # current mouse state
    mouse_x = 0
    mouse_y = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # DEBUG load test image
        self.load_image(Image.open("/home/brice/Données/Temp/pic.jpg"))

        # zoom
        self.zoom_spinbutton.set_range(0.1, 10.0)
        self.zoom_spinbutton.set_increments(0.1, 1.0)
        self.zoom_spinbutton.set_value(1.0)

        # binding
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("motion-notify-event", self.mouse_move)
        self.drawing_area.connect("button-press-event", self.mouse_down)
        self.drawing_area.connect("button-release-event", self.mouse_up)
        self.drawing_area.set_events(Gdk.EventMask.ALL_EVENTS_MASK)

        # center window
        self.set_size_request(1024, 768)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

    def load_image(self, image):
        self.image = image
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        buffer.seek(0)

        # create cairo surface
        self.imageSurface = cairo.ImageSurface.create_from_png(buffer)

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

        def handle_response(d, r):
            if r == Gtk.ResponseType.OK:
                self.do_resize(d.width, d.height)
            d.destroy()

        dialog = ResizeDialog(self.image.size[0], self.image.size[1])
        dialog.set_transient_for(self) # link dialog to parent

        dialog.connect("response", handle_response)

        dialog.show_all()
        pass

    def do_resize(self, width, height):
        self.load_image(self.image.resize((int(width), int(height)), resample=Image.BILINEAR))
        self.redraw_image()

    @Gtk.Template.Callback("on_crop")
    def on_crop(self, widget):
        self.tool = AreaSelector()

    def redraw_image(self):
        self.drawing_area.queue_draw()

    def mouse_move(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.redraw_image()

    def mouse_down(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.tool != None:
            self.tool.mouse_down(self.drawing_area, self.imageSurface, self.mouse_x, self.mouse_y)

        self.redraw_image()

    def mouse_up(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.tool != None:
            self.tool.mouse_up(self.drawing_area, self.imageSurface, self.mouse_x, self.mouse_y)

        self.redraw_image()

    def on_draw(self, w, cr):

        # draw image given the scale factor
        self.drawing_area.set_size_request(self.scale * self.imageSurface.get_width(), self.scale * self.imageSurface.get_height())
        cr.scale(self.scale, self.scale)
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # test
        cr.set_source_rgb(1, 1, 0)
        cr.select_font_face("Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(40)
        cr.move_to(40, 40)
        cr.show_text("This is a test")

        # tool (scale back to 1/1)
        cr.scale(1/self.scale, 1/self.scale)

        if self.tool != None:
            self.tool.draw(w, cr, self.mouse_x, self.mouse_y)

