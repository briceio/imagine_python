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

from .document import Document
from .resize_dialog import ResizeDialog
from .tools import Tool, CropTool, AnnotationRectangleTool

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import cairo
import math
from PIL import Image

@Gtk.Template(resource_path='/io/boite/imagine/window.ui')
class ImagineWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ImagineWindow'

    # scale factor
    scale = 1.0

    # widgets
    drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    zoom_spinbutton: Gtk.SpinButton = Gtk.Template.Child()
    layers_listbox: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TODO DEBUG document
        self.document = Document("/home/brice/Données/Temp/pic.jpg")

        # current tool
        self.tool: Tool = None

        # current mouse state
        self.mouse_x = 0
        self.mouse_y = 0

        # zoom
        self.zoom_spinbutton.set_range(0.1, 10.0)
        self.zoom_spinbutton.set_increments(0.1, 1.0)
        self.zoom_spinbutton.set_value(1.0)

        # events
        self.connect("key-press-event", self.on_key_press)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("motion-notify-event", self.mouse_move)
        self.drawing_area.connect("button-press-event", self.mouse_down)
        self.drawing_area.connect("button-release-event", self.mouse_up)
        self.drawing_area.set_events(Gdk.EventMask.ALL_EVENTS_MASK)

        # binding
        self.layers_listbox.bind_model(self.document.layers, self.create_layer_item_widget)

        # center window
        self.set_size_request(1024, 768)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

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
        self.redraw()

    @Gtk.Template.Callback("on_resize")
    def on_resize(self, widget):

        def handle_response(d, r):
            if r == Gtk.ResponseType.OK:
                self.do_resize(d.width, d.height)
            d.destroy()

        dialog = ResizeDialog(self.document.image.size[0], self.document.image.size[1])
        dialog.set_transient_for(self) # link dialog to parent

        dialog.connect("response", handle_response)

        dialog.show_all()

    def do_resize(self, width, height):
        self.document.resize(int(width), int(height))
        self.redraw()

    @Gtk.Template.Callback("on_crop")
    def on_crop(self, widget):
        self.set_active_tool(CropTool(self.document))

    @Gtk.Template.Callback("on_annotate_rectangle")
    def on_annotate_rectangle(self, widget):
        self.set_active_tool(AnnotationRectangleTool(self.document))

    def set_active_tool(self, tool, keep_selected = False):
        def apply_callback():
            # unselect if requested
            if not keep_selected:
                self.tool = None

        self.tool = tool
        self.tool.apply_callback = apply_callback

    def redraw(self):
        self.drawing_area.queue_draw()

    def mouse_move(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.redraw()

    def mouse_down(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.tool != None:
            self.tool.mouse_down(self.document, self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y)

        self.redraw()

    def mouse_up(self, w, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        if self.tool != None:
            self.tool.mouse_up(self.document, self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y)

        self.redraw()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.tool != None:
                self.tool.cancel()
                self.redraw()

    def create_layer_item_widget(self, layer):
        return Gtk.Label(label = layer.name)

    def on_draw(self, w, cr):

        # document
        self.drawing_area.set_size_request(self.scale * self.document.imageSurface.get_width(), self.scale * self.document.imageSurface.get_height())
        cr.scale(self.scale, self.scale)

        self.document.draw(w, cr)

        # scale back to 1/1
        cr.scale(1/self.scale, 1/self.scale)

        # tools
        if self.tool != None:
            self.tool.draw(self.document, w, cr, self.mouse_x, self.mouse_y)

