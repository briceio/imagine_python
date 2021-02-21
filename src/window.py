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
import functools, operator

MOUSE_SCROLL_FACTOR = 2.0

@Gtk.Template(resource_path='/io/boite/imagine/window.ui')
class ImagineWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ImagineWindow'

    # documents
    documents = Gio.ListStore()

    # current document
    document = GObject.Property(type=Document)

    # widgets
    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    scroll_area: Gtk.ScrolledWindow = Gtk.Template.Child()
    viewport: Gtk.Viewport = Gtk.Template.Child()
    drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    zoom_spinbutton: Gtk.SpinButton = Gtk.Template.Child()
    layers_listbox: Gtk.ListBox = Gtk.Template.Child()
    documents_listbox: Gtk.ListBox = Gtk.Template.Child()
    layer_editor_container: Gtk.Box = Gtk.Template.Child()
    button_save: Gtk.Button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # current tool
        self._browsing = False
        self._browsing_prev_x = 0
        self._browsing_prev_y = 0
        self._skip_browse_signal = False
        self._saving = False
        self.tool: Tool = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.selected_layer: Layer = None

        # register the accelerator
        self.accelerator = Accelerator(activation_timeout=1.0)
        self.accelerator.disable()
        self.accelerator.add(None, "Tab", lambda: self._switch_document())
        self.accelerator.add("document", "<Primary>w", lambda: self.on_file_close(None))
        self.accelerator.add("document", "r", lambda: self.on_resize(None))
        self.accelerator.add("document", "<Primary>s", lambda: self.on_file_save(None))
        self.accelerator.add("document", "s,a", lambda: self.on_file_save_all(None))
        self.accelerator.add("document", "s,s", lambda: self.on_file_save_as(None))
        self.accelerator.add("document", "c", lambda: self.on_crop(None))
        self.accelerator.add("document", "r,l", lambda: self.on_rotate_left(None))
        self.accelerator.add("document", "r,r", lambda: self.on_rotate_right(None))
        self.accelerator.add("document", "f,h", lambda: self.on_flip_horizontal(None))
        self.accelerator.add("document", "f,v", lambda: self.on_flip_vertical(None))
        self.accelerator.add("document", "a,p", lambda: self.on_annotate_path(None))
        self.accelerator.add("document", "a,r", lambda: self.on_annotate_rectangle(None))
        self.accelerator.add("document", "a,l", lambda: self.on_annotate_line(None))
        self.accelerator.add("document", "a,a", lambda: self.on_annotate_arrow(None))
        self.accelerator.add("document", "a,e", lambda: self.on_annotate_ellipse(None))
        self.accelerator.add("document", "a,c", lambda: self.on_annotate_circle(None))
        self.accelerator.add("document", "a,t", lambda: self.on_annotate_text(None))
        self.accelerator.add("document", "a,j", lambda: self.on_annotate_emoji(None))
        self.accelerator.add("document", "a,z", lambda: self.on_annotate_zoom(None))
        self.accelerator.add("document", "a,i", lambda: self.on_annotate_image(None))
        self.accelerator.add("document", "e,l", lambda: self.on_enhance_lighting(None))
        self.accelerator.add("document", "e,b", lambda: self.on_enhance_blur(None))
        self.connect("key-press-event", self.accelerator.key_handler)
        self.scroll_area.connect("enter-notify-event", lambda w, e: self.accelerator.enable())
        self.scroll_area.connect("leave-notify-event", lambda w, e: self.accelerator.disable())
        self.connect("destroy", lambda e: self.accelerator.stop())

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

        # zoom
        self.zoom_spinbutton.set_range(0.1, 10.0)
        self.zoom_spinbutton.set_increments(0.1, 1.0)
        self.zoom_spinbutton.set_value(1.0)

        # events
        self.connect("key-press-event", self.on_key_press)
        self.connect("delete-event", self.on_exit_app)
        self.drawing_area.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.drawing_area.connect("scroll-event", self.on_scroll)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("motion-notify-event", self.mouse_move)
        self.drawing_area.connect("button-press-event", self.mouse_down)
        self.drawing_area.connect("button-release-event", self.mouse_up)

        # documents binding
        self.documents_listbox.bind_model(self.documents, self._create_document_item_widget)
        self.documents_listbox.connect("row-selected", self._on_select_document)

        # binding
        self.button_save.bind_property("sensitive", self, "document")

    def load(self, path):
        # check if the file is already opened
        existing = [i for i, doc in enumerate(self.documents) if doc.path == path]

        if len(existing) > 0:
            # select existing file which already opened
            self.documents_listbox.select_row(self.documents_listbox.get_row_at_index(existing[0]))
        else:
            # load new document and select it
            self.document = Document(path)
            self.documents.append(self.document)
            self.documents_listbox.select_row(self.documents_listbox.get_row_at_index(len(self.documents) - 1))

    def _save(self, document=None):
        if document == None: document = self.document
        if document == None: return

        def save_png(surface):
            surface.write_to_png(path)

        def save_jpg(surface):
            image = Image.frombuffer(mode = 'RGBA', size = (width, height), data = surface.get_data(),)
            b, g, r, a = image.split()
            image = Image.merge('RGB', (r, g, b))
            image.save(path, quality=90)

        width, height = document.image.size

        path = document.path

        self._saving = True

        switcher = {
            ".jpg": save_jpg,
            ".jpeg": save_jpg,
            ".png": save_png
        }

        with cairo.ImageSurface(cairo.FORMAT_RGB24, width, height) as surface:
            context = cairo.Context(surface)
            self._draw_document(self, context, document)

            # save
            saver = switcher[document.extension]
            if saver != None:
                saver(surface)
            else:
                print("Unsupported format!") # TODO info box message

        self._saving = False

        document.dirty = False

        print("Saved to: %s" % path) # TODO info box message

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

        dialog.set_select_multiple(True)

        filter = Gtk.FileFilter()
        filter.set_name("Images")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        dialog.add_filter(filter)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            for filename in dialog.get_filenames():
                self.load(filename)

        dialog.destroy()

    @Gtk.Template.Callback("on_file_save")
    def on_file_save(self, widget):
        self._save()

    @Gtk.Template.Callback("on_file_save_as")
    def on_file_save_as(self, widget):
        if self.document == None: return

        dialog = Gtk.FileChooserDialog("Save destination", self, Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE_AS, Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.set_name("Images")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        dialog.add_filter(filter)

        dialog.set_filename(self.document.path)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.document.rename(dialog.get_filename())
            self._save()
            self.document = self.document

        dialog.destroy()

    @Gtk.Template.Callback("on_file_close")
    def on_file_close(self, widget):
        # TODO check dirty
        index = self.documents_listbox.get_selected_row().get_index()
        self._switch_document()
        self.documents.remove(index)

    @Gtk.Template.Callback("on_file_save_all")
    def on_file_save_all(self, widget):
        for document in self.documents:
            self._save(document)

        # TODO toast notification
        print("Save all done")

    @Gtk.Template.Callback("on_zoom_changed")
    def on_zoom_changed(self, widget):
        if self.document == None: return
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

    @Gtk.Template.Callback("on_annotate_path")
    def on_annotate_path(self, widget):
        self.set_active_tool(PathAnnotationTool(self.document), keep_selected=True)

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

    @Gtk.Template.Callback("on_annotate_image")
    def on_annotate_image(self, widget):
        self.set_active_tool(ImageAnnotationTool(self.document), keep_selected=True)

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

    def _switch_document(self):
        index = self.documents_listbox.get_selected_row().get_index()
        index = index + 1 if index < len(self.documents) - 1 else 0
        new_row = self.documents_listbox.get_row_at_index(index)
        if new_row != None:
            self.documents_listbox.select_row(new_row)
        else:
            self._set_header_subtitle(None)
            self.document = None # no more document in the stack

    def set_active_tool(self, tool, keep_selected = False):
        def apply_callback():
            # unselect if requested
            if not keep_selected:
                self.tool = None

        self.tool = tool
        self.tool.apply_callback = apply_callback

    def redraw(self):
        self.drawing_area.queue_draw()

    def _set_header_subtitle(self, subtitle):
        self.header_bar.set_subtitle(subtitle)

    def mouse_move(self, w, event):
        if self.document == None: return

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
        if self.document == None: return

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
        if self.document == None: return

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
        if self.document == None: return

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
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.keyval == Gdk.KEY_Escape:
            if self.tool != None:
                # cancel tool
                self.tool.cancel()
                self.tool = None
                # redraw
                self.redraw()
        elif (event.keyval == Gdk.KEY_Delete or event.keyval == Gdk.KEY_BackSpace) and event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            # remove current layer
            self.document.delete_layer(self.selected_layer)
            # redraw
            self.redraw()

    def on_exit_app(self, widget, event):

        # build up dirt documents list
        dirty_documents = ["▸ %s\n" % document.name for document in self.documents if document.dirty]

        if len(dirty_documents) > 0:
            dirty_docs_list = functools.reduce(operator.add, dirty_documents)

            dialog = Gtk.MessageDialog(parent=self, type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO)
            dialog.set_title("Warning !")
            dialog.format_secondary_markup("<b>There %s <u>%d document%s</u> not saved:</b>\n\n%s\nDo you really want to quit?" % ("is" if len(dirty_documents) <= 1 else "are", len(dirty_documents), "s" if len(dirty_documents) > 1 else "", dirty_docs_list))

            response = dialog.run()

            dialog.destroy()

            if response == Gtk.ResponseType.NO:
                return True

        return False

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
        document.bind_property("name", label, "label")
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
        if self.document == None:
            self._set_header_subtitle(None)
            return

        # document title
        self._set_header_subtitle(self.document.path)

        # deselect tool
        if self.tool != None:
            self.tool.cancel()
            self.tool = None

        self.document.on_updated_layers_list = self._on_updated_layers_list
        self.document.bind_property("scale", self.zoom_spinbutton, "value")
        self.zoom_spinbutton.set_value(self.document.scale)

        self.layers_listbox.bind_model(self.document.layers, self._create_layer_item_widget)
        self.layers_listbox.connect("row-selected", self._on_select_layer)

        self._offset_scroll_area(self.document.scroll_offset_x, self.document.scroll_offset_y, absolute=True)

        # accelerator context
        self.accelerator.set_context("document")

    def _on_select_document(self, container, row):

        # cleanup
        if self.document != None:
            self.document.on_updated_layers_list = None

        # switch document
        self.document = self.documents[row.get_index()] if len(self.documents) > 0 else None

        # redraw
        self.redraw()

    def _on_select_layer(self, container, row):

        # deselect tool
        if self.tool != None:
            self.tool.cancel()
            self.tool = None

        # cleanup layer editor
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
            self.redraw()

        # cleanup
        self._cleanup_layer_editor()

        # add the new editor
        layer_editor = LayerEditor(layer)
        layer_editor.on_update = on_update_editor
        self.layer_editor_container.add(layer_editor)

    def _draw_document(self, w, cr, document):

        # clipping
        iw, ih = document.image.size
        cr.rectangle(0, 0, iw, ih)
        cr.clip()

        # render document
        document.draw(w, cr)

    def on_draw(self, w, cr):

        # nothing to draw?
        if self.document == None:
            self.drawing_area.set_size_request(0, 0)
            return

        # scaling
        iw, ih = self.document.image.size
        if not self._saving:
            w = self.document.scale * iw
            h = self.document.scale * ih
            self.drawing_area.set_size_request(w, h)
            cr.scale(self.document.scale, self.document.scale)

        self._draw_document(w, cr, self.document)

        # tools
        if not self._saving and self.tool != None:
            self.tool.draw(self.document, w, cr, self.mouse_x, self.mouse_y)
