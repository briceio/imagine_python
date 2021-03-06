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
from .layer_editor import LayerEditor
from .accelerator import Accelerator
from .layers import *
from .extensions import *
from .gtk_extensions import *
from .history import *

from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf
import cairo
import math
from PIL import Image
import functools, operator
from urllib.parse import urlparse, unquote
import os

MOUSE_SCROLL_FACTOR = 2.0

@Gtk.Template(resource_path='/io/boite/imagine/window.ui')
class ImagineWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ImagineWindow'

    # settings
    USER_SETTINGS = Gio.Settings.new("imagine.user-settings")

    # documents
    documents = Gio.ListStore()

    # current document
    document = GObject.Property(type=Document)

    # widgets
    label_subtitle: Gtk.Label = Gtk.Template.Child()
    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    infobar: Gtk.InfoBar = Gtk.Template.Child()
    infobar_label: Gtk.Label = Gtk.Template.Child()
    main_paned: Gtk.Paned = Gtk.Template.Child()
    scroll_area: Gtk.ScrolledWindow = Gtk.Template.Child()
    viewport: Gtk.Viewport = Gtk.Template.Child()
    drawing_area: Gtk.DrawingArea = Gtk.Template.Child()
    zoom_spinbutton: Gtk.SpinButton = Gtk.Template.Child()
    layers_listbox: Gtk.ListBox = Gtk.Template.Child()
    documents_listbox: Gtk.ListBox = Gtk.Template.Child()
    layer_editor_container: Gtk.Box = Gtk.Template.Child()
    button_save: Gtk.Button = Gtk.Template.Child()
    menu_advanced_save: Gtk.MenuButton = Gtk.Template.Child()
    menu_advanced_zoom: Gtk.MenuButton = Gtk.Template.Child()
    zoom_spinbutton_label: Gtk.Label = Gtk.Template.Child()
    history_listbox: Gtk.ListBox = Gtk.Template.Child()
    popover_history: Gtk.Popover = Gtk.Template.Child()
    button_history: Gtk.Button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._browsing = False
        self._browsing_prev_x = 0
        self._browsing_prev_y = 0
        self._skip_browse_signal = False
        self._saving = False
        self.mouse_x = 0
        self.mouse_y = 0
        self.selected_layer: Layer = None

        # infobar
        self.infobar.set_revealed(False)

        # register the accelerator
        self.accelerator = Accelerator(activation_timeout=1.0)
        self.accelerator.add(None, "Tab", lambda: self._switch_document())
        self.accelerator.add("document", "Delete", lambda: self.delete_current_layer(None))
        self.accelerator.add("document", "BackSpace", lambda: self.delete_current_layer(None))
        self.accelerator.add("document", "Escape", lambda: self.unselect_layer(None))
        self.accelerator.add("document", "<Primary>z", lambda: self.document.history.undo())
        self.accelerator.add("document", "<Primary>w", lambda: self.on_file_close(None))
        self.accelerator.add("document", "r", lambda: self.on_resize(None), wait_timeout=True)
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
        self.accelerator.add("document", "a,d", lambda: self.on_annotate_clone(None))
        self.accelerator.add("document", "a,t", lambda: self.on_annotate_text(None))
        self.accelerator.add("document", "a,j", lambda: self.on_annotate_emoji(None))
        self.accelerator.add("document", "a,z", lambda: self.on_annotate_zoom(None))
        self.accelerator.add("document", "a,i", lambda: self.on_annotate_image(None))
        self.accelerator.add("document", "e,l", lambda: self.on_enhance_lighting(None))
        self.accelerator.add("document", "e,b", lambda: self.on_enhance_blur(None))
        self.accelerator.add("document", "z,z", lambda: self.on_zoom_100(None))
        self.accelerator.add("document", "z,a", lambda: self.on_zoom_best_fit(None))
        self.accelerator.add("document", "Up", lambda: self.document.move_layer(self.selected_layer, -1))
        self.accelerator.add("document", "Down", lambda: self.document.move_layer(self.selected_layer, 1))
        self.accelerator.add("document", "Page_Up", lambda: self._switch_document(-1))
        self.accelerator.add("document", "Page_Down", lambda: self._switch_document(1))
        self.connect("key-press-event", self.accelerator.key_handler)
        self.connect("destroy", lambda e: self.accelerator.stop())
        self.accelerator.enable()

        # contextual layer menu
        self.layer_menu = Menu()
        self.layer_menu.add_entry("Delete", lambda _: self.delete_current_layer(None), stock_id=Gtk.STOCK_DELETE)
        self.layer_menu.add_separator()
        self.layer_menu.add_entry("Move Up", lambda _: self.document.move_layer(self.selected_layer, -1), stock_id=Gtk.STOCK_GO_DOWN)
        self.layer_menu.add_entry("Move Down", lambda _: self.document.move_layer(self.selected_layer, 1), stock_id=Gtk.STOCK_GO_UP)
        self.layer_menu.show_all()

        # window management
        self._load_window_state()
        self.connect("configure-event", self._save_window_state)

        # document notify
        self.connect("notify::document", self._on_document_mounted)

        # zoom
        self.zoom_spinbutton.set_range(10, 1000)
        self.zoom_spinbutton.set_increments(10, 100)
        self.zoom_spinbutton.set_digits(0)
        self.zoom_spinbutton.set_value(100)

        # events
        self.connect("key-press-event", Layer.on_key)
        self.connect("key-release-event", Layer.on_key)
        self.connect("delete-event", self.on_exit_app)
        self.drawing_area.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.drawing_area.connect("scroll-event", self.on_scroll)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("motion-notify-event", self.mouse_move)
        self.drawing_area.connect("button-press-event", self.mouse_down)
        self.drawing_area.connect("button-release-event", self.mouse_up)

        # enable drag & drop
        self.connect("drag-data-received", self.on_drag_data_received)
        self.drawing_area.connect("drag-data-received", self.on_drop_image)
        self.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                  [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)
        self.drawing_area.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                  [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)


        # binding
        self.documents_listbox.bind_model(self.documents, self._create_document_item_widget)
        self.documents_listbox.connect("row-selected", self._on_select_document)
        self.layers_listbox.connect("row-selected", self._on_select_layer)
        self.button_save.bind_property("sensitive", self, "document")
        self.history_listbox.connect("row-activated", self._on_select_history)

        # hide subtitle
        self._set_header_subtitle(None)

        # init
        self._on_document_mounted(self, self.document)

    def load(self, path):
        # check if the file is already opened
        existing = [i for i, doc in enumerate(self.documents) if doc.path == path]

        if len(existing) > 0:
            # select existing file which already opened
            self.documents_listbox.select_row(self.documents_listbox.get_row_at_index(existing[0]))
        else:
            # load new document
            document = Document(path)
            self.documents.append(document)

            # trigger bindings
            self.document = document

    def _save(self, document=None):
        if document == None: document = self.document
        if document == None: return

        def save_png(surface):
            surface.write_to_png(path)

        def save_jpg(surface):
            image = pil_from_cairo_surface(surface)
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
            document.draw(self, context, self.mouse_x, self.mouse_y, helpers=False)

            # save
            saver = switcher[document.extension]
            if saver != None:
                saver(surface)
            else:
                self.display_message("Unsupported file format: %s" % document.extension)

        self._saving = False

        document.dirty = False

        self.display_message("File saved to: %s" % path)

    def _load_window_state(self):
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_default_size(ImagineWindow.USER_SETTINGS.get_int("window-width"), ImagineWindow.USER_SETTINGS.get_int("window-height"))

    def _save_window_state(self, window, event=None):
        ImagineWindow.USER_SETTINGS.set_int("window-width", self.get_size()[0])
        ImagineWindow.USER_SETTINGS.set_int("window-height", self.get_size()[1])

    def display_message(self, message, type=Gtk.MessageType.INFO):
        self.infobar_label.set_text(message)
        self.infobar.set_message_type(type)
        self.infobar.set_revealed(True)
        self.hide_message()

    @delay(3.0)
    def hide_message(self):
        self.infobar.set_revealed(False)

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
        row = self.documents_listbox.get_selected_row()
        if row != None:
            index = row.get_index()
            document = self.documents[index]

            # check dirty
            if document.dirty:
                dialog = Gtk.MessageDialog(parent=self, type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO)
                dialog.set_title("Closing %s" % document.name)
                dialog.format_secondary_markup("This image has been modified!\n\nDo you want to save it before?")

                response = dialog.run()

                dialog.destroy()

                if response == Gtk.ResponseType.YES:
                    self._save(document)

            self._switch_document()
            self.documents.remove(index)

    @Gtk.Template.Callback("on_file_save_all")
    def on_file_save_all(self, widget):
        for document in self.documents:
            self._save(document)

        self.display_message("All modified files saved successfully.")

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
        self.create_layer(CropLayer(self.document))

    @Gtk.Template.Callback("on_annotate_path")
    def on_annotate_path(self, widget):
        self.create_layer(PathAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_rectangle")
    def on_annotate_rectangle(self, widget):
        self.create_layer(RectangleAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_ellipse")
    def on_annotate_ellipse(self, widget):
        self.create_layer(EllipseAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_circle")
    def on_annotate_circle(self, widget):
        self.create_layer(CircleAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_line")
    def on_annotate_line(self, widget):
        self.create_layer(LineAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_arrow")
    def on_annotate_arrow(self, widget):
        self.create_layer(LineAnnotationLayer(self.document, arrow=True))

    @Gtk.Template.Callback("on_annotate_text")
    def on_annotate_text(self, widget):
        self.create_layer(TextAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_emoji")
    def on_annotate_emoji(self, widget):
        self.create_layer(EmojiAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_zoom")
    def on_annotate_zoom(self, widget):
        self.create_layer(ZoomAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_image")
    def on_annotate_image(self, widget):
        self.create_layer(ImageAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_annotate_clone")
    def on_annotate_clone(self, widget):
        self.create_layer(CloneAnnotationLayer(self.document))

    @Gtk.Template.Callback("on_enhance_lighting")
    def on_enhance_lighting(self, widget):
        self.create_layer(LightingLayer(self.document))

    @Gtk.Template.Callback("on_enhance_blur")
    def on_enhance_blur(self, widget):
        self.create_layer(BlurLayer(self.document))

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

    @Gtk.Template.Callback("on_zoom_100")
    def on_zoom_100(self, _):
        self.document.scale = 100

    @Gtk.Template.Callback("on_zoom_best_fit")
    def on_zoom_best_fit(self, _):
        self.document.scale = self._get_best_fit_document_scale(self.document)

    @Gtk.Template.Callback("on_layer_button_press")
    def on_layer_button_press(self, widget, event):
        if event.button == 3:
            hits = self.document.get_layers_at_position(event.x, event.y)
            if len(hits) >= 1:
                self.selected_layer = hits[0]
                self.layer_menu.popup_at_pointer(event)

    @Gtk.Template.Callback("on_settings")
    def on_settings(self, widget):
        os.system("dconf-editor /apps/imagine &")

    @Gtk.Template.Callback("on_about")
    def on_about(self, widget):
        dialog = Gtk.AboutDialog(copyright="Brice MARTIN (brice@boite.io)",
                                 authors=["Brice MARTIN (brice@boite.io)"],
                                 license_type=Gtk.License.GPL_3_0,
                                 program_name="Imagine",
                                 version="1.0",
                                 website="https://boite.io",
                                 website_label="Boite",
                                 comments="A minimalist yet powerful image annotation tool.")
        # TODO logo=[pixbuf]
        # TODO automate version injection
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()

    def _get_best_fit_document_scale(self, document):
        source_w, source_h = document.image.size
        target_w, target_h = self.scroll_area.get_allocated_width(), self.scroll_area.get_allocated_height()

        source_ratio = source_w / source_h
        target_ratio = target_w / target_h

        if source_ratio >= target_ratio:
            scale_x = target_w / source_w
            scale_y = scale_x
        else:
            scale_y = target_h / source_h
            scale_x = scale_y

        return min(scale_x, scale_y) * 100

    def _switch_document(self, offset=1):
        row = self.documents_listbox.get_selected_row()
        if row != None:
            index = row.get_index()
            index = (index + offset) % len(self.documents)
            new_row = self.documents_listbox.get_row_at_index(index)
            if new_row != None:
                self.documents_listbox.select_row(new_row)
            else:
                self._set_header_subtitle(None)
                self.document = None # no more document in the stacky

    def create_layer(self, layer):
        self.document.add_layer(layer)

    def redraw(self):
        self.drawing_area.queue_draw()

    def _set_header_subtitle(self, subtitle):
        if subtitle != None:
            self.label_subtitle.set_text(subtitle)
            self.label_subtitle.show()
        else:
            self.label_subtitle.hide()

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
            self.mouse_x = event.x / (self.document.scale / 100)
            self.mouse_y = event.y / (self.document.scale / 100)

            if self.selected_layer != None:
                self.selected_layer.mouse_move(self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y)

            self.redraw()

    def mouse_down(self, w, event):
        if self.document == None: return

        self.mouse_x = event.x / (self.document.scale / 100)
        self.mouse_y = event.y / (self.document.scale / 100)

        if not self._browsing and event.button == 2:
            self._browsing_prev_x = event.x
            self._browsing_prev_y = event.y
            self._browsing = True
            self._remember_scroll_offset()
        elif self.selected_layer != None:
            handled = self.selected_layer.mouse_down(self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y, event.button)

            if not handled:
                # try to select another tool
                hits = self.document.get_layers_positions_at_position(event.x, event.y)
                if len(hits) >= 1:
                    self.layers_listbox.select_row(self.layers_listbox.get_row_at_index(hits[0]))

        self.redraw()

    def mouse_up(self, w, event):
        if self.document == None: return

        self.mouse_x = event.x / (self.document.scale / 100)
        self.mouse_y = event.y / (self.document.scale / 100)

        if self._browsing and event.button == 2:
            self._browsing = False
        elif self.selected_layer != None:
            self.selected_layer.mouse_up(self.drawing_area, self.document.imageSurface, self.mouse_x, self.mouse_y, event.button)

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
                self.document.scale = min(self.zoom_spinbutton.get_range()[1], self.document.scale + 25)
            else:
                self.document.scale = max(self.zoom_spinbutton.get_range()[0], self.document.scale - 25)

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

    def unselect_layer(self, _):
        if self.selected_layer != None:
            # remove transient layer
            if self.selected_layer.transient or self.selected_layer.dirty:
                self.document.delete_layer(self.selected_layer, dirty=False)
            # cancel operations on layer
            self.selected_layer = None
            # redraw
            self.redraw()

    def delete_current_layer(self, _):
        # remove current layer
        self.document.delete_layer(self.selected_layer)
        # redraw
        self.redraw()

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if info == 80:
            for uri in data.get_uris():
                self.load(unquote(urlparse(uri).path))

    def on_drop_image(self, widget, drag_context, x, y, data, info, time):
        if info == 80:
            offset = 0
            for uri in data.get_uris():
                path = unquote(urlparse(uri).path)
                layer = ImageAnnotationLayer(self.document, x1=x+offset, y1=y+offset, x2=x+offset+192, y2=y+offset+192, path=path)
                self.document.add_layer(layer)
                offset += 30

    def on_exit_app(self, widget, event):

        # build up dirty documents list
        dirty_documents = ["??? %s\n" % document.name for document in self.documents if document.dirty]

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

    def _create_history_item_widget(self, snapshot):
        return Gtk.Label(snapshot.description)

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

        def update_label_state(layer, _, label):
            if layer.enabled:
                label.set_text(layer.name)
            else:
                label.set_markup("<s>%s</s>" % layer.name)
            label.set_sensitive(layer.enabled)

        box = Gtk.HBox()
        box.set_size_request(-1, 30)
        box.set_homogeneous(False)

        # label
        label = Gtk.Label(label = layer.name)
        layer.connect("notify::name", update_label_state, label)
        layer.connect("notify::enabled", update_label_state, label)
        update_label_state(layer, None, label)
        box.pack_start(label, True, True, 0)

        # commands
        buttons = Gtk.HBox()
        buttons.set_homogeneous(True)
        buttons.set_size_request(30, -1)

        delete_button = Gtk.ToolButton(stock_id = Gtk.STOCK_DELETE)
        delete_button.connect("clicked", delete_layer, layer)
        buttons.add(delete_button)

        down_button = Gtk.ToolButton(stock_id = Gtk.STOCK_GO_DOWN)
        down_button.connect("clicked", move_layer, layer, 1)
        down_button.set_sensitive(not layer.is_last_layer())
        buttons.add(down_button)

        up_button = Gtk.ToolButton(stock_id = Gtk.STOCK_GO_UP)
        up_button.connect("clicked", move_layer, layer, -1)
        up_button.set_sensitive(not layer.is_first_layer())
        buttons.add(up_button)

        enable_button = Gtk.CheckButton()
        layer.bind_property("enabled", enable_button, "active", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        buttons.add(enable_button)

        box.pack_end(buttons, False, False, 0)

        box.show_all()

        return box

    def _on_document_mounted(self, window, document):

        # no document
        if self.document == None:
            # remove title
            self._set_header_subtitle(None)

            # hide the UI
            self.main_paned.hide()
            self.button_save.hide()
            self.menu_advanced_save.hide()
            self.menu_advanced_zoom.hide()
            self.button_history.hide()

            return

        # bind UI
        self.document.bind_property("dirty", self.button_save, "sensitive", GObject.BindingFlags.SYNC_CREATE)
        self.document.connect("notify::dirty", lambda _, __: self.redraw())

        # ensure UI visibility
        self.main_paned.show()
        self.button_save.show()
        self.menu_advanced_save.show()
        self.menu_advanced_zoom.show()
        self.button_history.show()

        # document title
        self._set_header_subtitle(self.document.path)

        # deselect layer
        if self.selected_layer != None:
            self.selected_layer = None

        self.document.on_updated_layers_list = self._on_updated_layers_list
        self.document.bind_property("scale", self.zoom_spinbutton, "value")
        self.zoom_spinbutton.set_value(self.document.scale)

        self._offset_scroll_area(self.document.scroll_offset_x, self.document.scroll_offset_y, absolute=True)

        # accelerator context
        self.accelerator.set_context("document")

        # select newly mounted document
        found, position = self.documents.find(self.document)
        if found:
            self.documents_listbox.select_row(self.documents_listbox.get_row_at_index(position))

        # bind history
        self.history_listbox.bind_model(self.document.history.snapshots, self._create_history_item_widget)

    def _select_last_document(self):
        self.documents_listbox.select_row(self.documents_listbox.get_row_at_index(len(self.documents) - 1))

    def _on_select_document(self, container, row):

        # no more selection, hide the paned
        self.main_paned.set_position(150 if row != None else 0)

        # cleanup
        if self.document != None:
            self.document.on_updated_layers_list = None

        # switch document
        self.document = self.documents[row.get_index()] if len(self.documents) > 0 else None

        # bind
        self.layers_listbox.bind_model(self.document.layers, self._create_layer_item_widget)

        # redraw
        self.redraw()

    def _on_select_history(self, container, row):

        # get current document history snapshot entry
        if row != None:
            index = row.get_index()
            self.document.history.rollback(index)
            self.popover_history.hide()
            self.display_message("%d modification%s cancelled." % (index + 1, "s" if index + 1 > 1 else ""))

    def _on_select_layer(self, container, row):

        # deselect layer
        if self.selected_layer != None:
            self.selected_layer = None

        # cleanup layer editor
        if row == None:
            self._cleanup_layer_editor()
            return

        # get the selected layer
        self.selected_layer = self.document.layers[row.get_index()]

        # update the active flags
        for layer in self.document.layers:
            layer.active = layer == self.selected_layer

        # udpate the layer properties editor
        self._build_layer_editor(self.selected_layer)

        # bind enabled/disabled flag on redraw refresh
        self.selected_layer.connect("notify::enabled", lambda layer, _: self.redraw())

        # redraw
        self.redraw()

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

        # cleanup
        self._cleanup_layer_editor()

        # add the new editor
        layer_editor = LayerEditor(layer)
        layer.connect("notify", lambda _, __: self.redraw())
        self.layer_editor_container.add(layer_editor)

    def on_draw(self, w, cr):

        # nothing to draw?
        if self.document == None:
            self.drawing_area.set_size_request(0, 0)
            return

        # scaling
        iw, ih = self.document.image.size
        if not self._saving:
            w = (self.document.scale / 100) * iw
            h = (self.document.scale / 100) * ih
            self.drawing_area.set_size_request(w, h)
            cr.scale(self.document.scale / 100, self.document.scale / 100)

        # draw document
        cr.save()
        self.document.draw(w, cr, self.mouse_x, self.mouse_y, helpers=True)
        cr.restore()

