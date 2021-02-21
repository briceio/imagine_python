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
from .tools import *
from .layer_editor import LayerEditor
from .accelerator import Accelerator
#
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GdkPixbuf
import cairo
import math
from PIL import Image

MOUSE_SCROLL_FACTOR = 2.0

@Gtk.Template(resource_path='/io/boite/imagine/window.ui')
class ImagineWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ImagineWindow'

    # documents
    documents = Gio.ListStore()

    # current document
    document = GObject.Property(type=Document)

    # widgets
    scroll_area: Gtk.ScrolledWindow = Gtk.Template.Child()
    viewport: Gtk.Viewport = Gtk.Template.Child()
    drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    zoom_spinbutton: Gtk.SpinButton = Gtk.Template.Child()
    layers_listbox: Gtk.ListBox = Gtk.Template.Child()
    documents_listbox: Gtk.ListBox = Gtk.Template.Child()
    layer_editor_container: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # load settings
        self.user_settings = Gio.Settings.new("imagine.user-settings")

        # window management
        self._load_window_state()
        self.connect("configure-event", self._save_window_state)

        # document notify
        self.connect("notify::document", self._on_document_mounted)

        # TODO DEBUG document
        self.load("/home/brice/Données/Temp/pic.jpg")
        self.load("/home/brice/Données/Temp/pic2.jpg")

        # current tool
        self.tool: Tool = None

        # current layer
        self.selected_layer: Layer = None

        # current document state
        self._saving = False

        # current mouse state
        self.mouse_x = 0
        self.mouse_y = 0

        # default is no browsing
        self._browsing = False
        self._browsing_prev_x = 0
        self._browsing_prev_y = 0
        self._skip_browse_signal = False

        # zoom
        self.zoom_spinbutton.set_range(0.1, 10.0)
        self.zoom_spinbutton.set_increments(0.1, 1.0)
        self.zoom_spinbutton.set_value(1.0)

        # register the accelerator
        self.accelerator = Accelerator(activation_key=Gdk.KEY_a)
        self.accelerator.add("general", "s", lambda: self.on_resize(None))
        self.accelerator.add("general", "c", lambda: self.on_crop(None))
        self.accelerator.add("general", "r,l", lambda: self.on_rotate_left(None))
        self.accelerator.add("general", "r,r", lambda: self.on_rotate_right(None))
        self.accelerator.add("general", "f,h", lambda: self.on_flip_horizontal(None))
        self.accelerator.add("general", "f,v", lambda: self.on_flip_vertical(None))
        self.accelerator.add("general", "a,r", lambda: self.on_annotate_rectangle(None))
        self.accelerator.add("general", "a,l", lambda: self.on_annotate_line(None))
        self.accelerator.add("general", "a,a", lambda: self.on_annotate_arrow(None))
        self.accelerator.add("general", "a,e", lambda: self.on_annotate_ellipse(None))
        self.accelerator.add("general", "a,c", lambda: self.on_annotate_circle(None))
        self.accelerator.add("general", "a,t", lambda: self.on_annotate_text(None))
        self.accelerator.add("general", "a,j", lambda: self.on_annotate_emoji(None))
        self.accelerator.add("general", "a,z", lambda: self.on_annotate_zoom(None))
        self.accelerator.add("general", "e,l", lambda: self.on_enhance_lighting(None))
        self.accelerator.add("general", "e,b", lambda: self.on_enhance_blur(None))
        self.accelerator.set_context("general")
        self.connect("key-press-event", self.accelerator.key_handler)
        self.scroll_area.connect("enter-notify-event", lambda w, e: self.accelerator.enable())
        self.scroll_area.connect("leave-notify-event", lambda w, e: self.accelerator.disable())
        self.connect("destroy", lambda e: self.accelerator.stop())

        # events
        self.connect("key-press-event", self.on_key_press)
        self.drawing_area.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.drawing_area.connect("scroll-event", self.on_scroll)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("motion-notify-event", self.mouse_move)
        self.drawing_area.connect("button-press-event", self.mouse_down)
        self.drawing_area.connect("button-release-event", self.mouse_up)

        # documents biding
        self.documents_listbox.bind_model(self.documents, self._create_document_item_widget)
        self.documents_listbox.connect("row-selected", self._on_select_document)

    def load(self, path):
        self.document = Document(path)
        self.documents.append(self.document)

    def _save(self):

        width, height = self.document.image.size

        path = "{path}-test.png".format(path = self.document.path)
        print("Saving (%d, %d) to: %s" % (width, height, path))

        self._saving = True

        with cairo.ImageSurface(cairo.FORMAT_RGB24, width, height) as surface:
            context = cairo.Context(surface)
            self.drawing_area.draw(context)
            surface.write_to_png(path)

        self._saving = False

        # TODO info box message
        print("Saved!")

    def _load_window_state(self):
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_default_size(self.user_settings.get_int("window-width"), self.user_settings.get_int("window-height"))

    def _save_window_state(self, window, event=None):
        self.user_settings.set_int("window-width", self.get_size()[0])
        self.user_settings.set_int("window-height", self.get_size()[1])

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
            self.load(dialog.get_filename())

        dialog.destroy()

    @Gtk.Template.Callback("on_file_save")
    def on_file_save(self, widget):
        self._save()

    @Gtk.Template.Callback("on_zoom_changed")
    def on_zoom_changed(self, widget):
        self.document.scale = self.zoom_spinbutton.get_value()
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
        self.set_active_tool(RectangleAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_ellipse")
    def on_annotate_ellipse(self, widget):
        self.set_active_tool(EllipseAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_circle")
    def on_annotate_circle(self, widget):
        self.set_active_tool(EllipseAnnotationTool(self.document, circle = True), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_line")
    def on_annotate_line(self, widget):
        self.set_active_tool(LineAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_arrow")
    def on_annotate_arrow(self, widget):
        self.set_active_tool(LineAnnotationTool(self.document, arrow=True), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_text")
    def on_annotate_text(self, widget):
        self.set_active_tool(TextAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_emoji")
    def on_annotate_emoji(self, widget):
        self.set_active_tool(EmojiAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_annotate_zoom")
    def on_annotate_zoom(self, widget):
        self.set_active_tool(ZoomAnnotationTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_rotate_left")
    def on_rotate_left(self, widget):
        self.document.rotate(90)
        self.redraw()

    @Gtk.Template.Callback("on_rotate_right")
    def on_rotate_right(self, widget):
        self.document.rotate(-90)
        self.redraw()

    @Gtk.Template.Callback("on_flip_horizontal")
    def on_flip_horizontal(self, widget):
        self.document.flip_horizontal()
        self.redraw()

    @Gtk.Template.Callback("on_flip_vertical")
    def on_flip_vertical(self, widget):
        self.document.flip_vertical()
        self.redraw()

    @Gtk.Template.Callback("on_enhance_lighting")
    def on_enhance_lighting(self, widget):
        self.set_active_tool(LightingTool(self.document), keep_selected=True)

    @Gtk.Template.Callback("on_enhance_blur")
    def on_enhance_blur(self, widget):
        self.set_active_tool(BlurTool(self.document), keep_selected=True)

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

        # browsing with the middle mouse button
        if self._browsing:
            delta_x = self._browsing_prev_x - event.x
            delta_y = self._browsing_prev_y - event.y

            if not self._skip_browse_signal: # hack
                self._offset_scroll_area(delta_x * MOUSE_SCROLL_FACTOR, delta_y * MOUSE_SCROLL_FACTOR)

            self._skip_browse_signal = not self._skip_browse_signal

            self._browsing_prev_x = event.x
            self._browsing_prev_y = event.y
        else:
            # tooling
            self.mouse_x = event.x / self.document.scale
            self.mouse_y = event.y / self.document.scale

            if self.tool != None:
                self.tool.mouse_move(self.document, self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y)

            self.redraw()

    def mouse_down(self, w, event):
        self.mouse_x = event.x / self.document.scale
        self.mouse_y = event.y / self.document.scale

        if not self._browsing and event.button == 2:
            self._browsing_prev_x = event.x
            self._browsing_prev_y = event.y
            self._browsing = True
            self._remember_scroll_offset()
        elif self.tool != None:
            self.tool.mouse_down(self.document, self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y, event.button)

        self.redraw()

    def mouse_up(self, w, event):
        self.mouse_x = event.x / self.document.scale
        self.mouse_y = event.y / self.document.scale

        if self._browsing and event.button == 2:
            self._browsing = False
        elif self.tool != None:
            self.tool.mouse_up(self.document, self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y, event.button)

        self.redraw()

    def _offset_scroll_area(self, x, y, absolute=False):
        adj_h = self.scroll_area.get_hadjustment()
        ox = x if absolute else adj_h.get_value() + x
        adj_h.set_value(ox)
        self.scroll_area.set_hadjustment(adj_h)

        adj_v = self.scroll_area.get_vadjustment()
        oy = y if absolute else adj_v.get_value() + y
        adj_v.set_value(oy)
        self.scroll_area.set_vadjustment(adj_v)

    def _remember_scroll_offset(self):
        # keep track of scrolling per document
        self.document.scroll_offset_x = self.scroll_area.get_hadjustment().get_value()
        self.document.scroll_offset_y = self.scroll_area.get_vadjustment().get_value()

    def on_scroll(self, widget, event):

        # zoom using mouse wheel & ctrl key
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            direction = event.get_scroll_deltas()[2]
            if direction < 0:
                self.document.scale = min(10.0, self.document.scale + 0.5)
            else:
                self.document.scale = max(0.1, self.document.scale - 0.5)

            # center zoom on mouse TODO bug not perfect
            rect, _ = self.scroll_area.get_allocated_size()

            offset_h = event.x - rect.width / 2
            offset_v = event.y - rect.height / 2

            self._offset_scroll_area(offset_h, offset_v)

            self._remember_scroll_offset()

            # redraw
            self.redraw()

            return True

        self._remember_scroll_offset()

        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.tool != None:
                # cancel tool
                self.tool.cancel()
                self.tool = None
                # redraw
                self.redraw()
        elif event.keyval == Gdk.KEY_Delete or event.keyval == Gdk.KEY_BackSpace:
            # remove current layer
            self.document.delete_layer(self.selected_layer)
            # redraw
            self.redraw()

    def _create_document_item_widget(self, document):

        def on_updated_thumbnail(document):
            thumbnail.set_from_pixbuf(document.thumbnail)

        box = Gtk.VBox()
        box.set_size_request(-1, 92)

        # thumbnail
        thumbnail = Gtk.Image(pixbuf = document.thumbnail)
        document.on_updated_thumbnail = on_updated_thumbnail
        box.pack_start(thumbnail, True, True, 0)

        # label
        label = Gtk.Label(label = document.name)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        box.pack_start(label, True, True, 0)

        box.show_all()
        return box

    def _create_layer_item_widget(self, layer):

        def delete_layer(widget, layer):
            self.document.delete_layer(layer)

        def move_layer(widget, layer, offset):
            self.document.move_layer(layer, offset)

        box = Gtk.HBox()
        box.set_size_request(-1, 30)
        box.set_homogeneous(False)

        # label
        label = Gtk.Label(label = layer.name)
        layer.bind_property("name", label, "label")
        box.pack_start(label, True, True, 0)

        # commands
        buttons = Gtk.HBox()
        buttons.set_homogeneous(True)
        buttons.set_size_request(30, -1)

        down_button = Gtk.ToolButton(stock_id = Gtk.STOCK_GO_DOWN)
        down_button.connect("clicked", move_layer, layer, 1)
        down_button.set_sensitive(not layer.is_last_layer())
        buttons.add(down_button)

        up_button = Gtk.ToolButton(stock_id = Gtk.STOCK_GO_UP)
        up_button.connect("clicked", move_layer, layer, -1)
        up_button.set_sensitive(not layer.is_first_layer())
        buttons.add(up_button)

        delete_button = Gtk.ToolButton(stock_id = Gtk.STOCK_DELETE)
        delete_button.connect("clicked", delete_layer, layer)
        buttons.add(delete_button)

        box.pack_end(buttons, False, False, 0)

        box.show_all()
        return box

    def _on_document_mounted(self, window, document):
        # TODO BUG this is called 3 times at start
        self.document.on_updated_layers_list = self._on_updated_layers_list
        self.document.bind_property("scale", self.zoom_spinbutton, "value")
        self.zoom_spinbutton.set_value(self.document.scale)

        self.layers_listbox.bind_model(self.document.layers, self._create_layer_item_widget)
        self.layers_listbox.connect("row-selected", self._on_select_layer)

        self._offset_scroll_area(self.document.scroll_offset_x, self.document.scroll_offset_y, absolute=True)

    def _on_select_document(self, container, row):

        # deselect tool
        if self.tool != None:
            self.tool.cancel()
            self.tool = None

        # cleanup
        if self.document != None:
            self.document.on_updated_layers_list = None

        # switch document
        self.document = self.documents[row.get_index()]
        self.redraw()

    def _on_select_layer(self, container, row):

        # cleanup
        if row == None:
            self._cleanup_layer_editor()
            return

        # build & select the default tool (if any)
        layer = self.document.layers[row.get_index()]
        tool_name = layer.get_tool()
        if tool_name != None:
            self.tool = globals()[tool_name](self.document, layer)

        # keep track of selected layer
        self.selected_layer = layer

        # udpate the layer properties editor
        self._build_layer_editor(layer)

    def _on_updated_layers_list(self, action, layer):

        # refresh layers list
        self.layers_listbox.bind_model(self.document.layers, self._create_layer_item_widget)

        # select first layer
        self.layers_listbox.select_row(self.layers_listbox.get_row_at_index(0))

        # redraw
        self.redraw()

    def _cleanup_layer_editor(self):
        for child in self.layer_editor_container.get_children():
            self.layer_editor_container.remove(child)

    def _build_layer_editor(self, layer):

        def on_update_editor(layer):
            self.redraw() # TODO redraw only layer?

        # cleanup
        self._cleanup_layer_editor()

        # add the new editor
        layer_editor = LayerEditor(layer)
        layer_editor.on_update = on_update_editor
        self.layer_editor_container.add(layer_editor)

    def on_draw(self, w, cr):

        # scaling
        iw, ih = self.document.image.size
        if not self._saving:
            w = self.document.scale * iw
            h = self.document.scale * ih
            self.drawing_area.set_size_request(w, h)
            cr.scale(self.document.scale, self.document.scale)

        # clipping
        cr.rectangle(0, 0, iw, ih)
        cr.clip()

        # render document
        self.document.draw(w, cr)

        # tools
        if not self._saving and self.tool != None:
            self.tool.draw(self.document, w, cr, self.mouse_x, self.mouse_y)

