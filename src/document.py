from PIL import Image
import cairo
from io import BytesIO
from gi.repository import Gtk, Gio, GObject, GdkPixbuf, GLib
import enum
import os
from .extensions import *
from .layers import Layer
from .history import *

class LayerAction(enum.Enum):
    ADD = 1
    DELETE = 2
    MOVE = 3

class Document(GObject.GObject):

    # callbacks
    on_updated_layers_list = None
    on_updated_thumbnail = None

    # scale
    scale = GObject.Property(type=int, default=100)

    # name
    name = GObject.Property(type=str)

    # dirty flag
    dirty = GObject.Property(type=bool, default=False)

    # history
    history = GObject.Property(type=History)

    def __init__(self, path):
        GObject.GObject.__init__(self)

        self.history = History()
        self.path = path
        self.name = os.path.basename(path)
        self.extension = os.path.splitext(path)[1]
        self.image: Image = None
        self._previous_layer_render: Image = None
        self.thumbnail: GdkPixbuf = None
        self.imageSurface: cairo.ImageSurface = None
        self.layers = Gio.ListStore()
        self._reload(Image.open(path))

        self.scroll_offset_x = 0
        self.scroll_offset_y = 0

    def _reload(self, image, dirty=False):

        # image
        self.image = image

        # thumbnail
        thumbnail = self.image.copy()
        thumbnail.thumbnail((92, 92), Image.ANTIALIAS)

        p_buffer = BytesIO()
        thumbnail.save(p_buffer, format="PNG")
        p_buffer.seek(0)

        loader = GdkPixbuf.PixbufLoader()
        loader.write(p_buffer.read())
        self.thumbnail = loader.get_pixbuf()
        loader.close()

        if self.on_updated_thumbnail != None:
            self.on_updated_thumbnail(self)

        # create cairo surface
        self.imageSurface = cario_image_from_pil(self.image)

        if dirty:
            self.dirty = True

    def rename(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.extension = os.path.splitext(path)[1]

    def resize(self, width, height):
        # capture state for rollback
        previous_image = self.image.copy()

        self.history.snapshot("Resize to (%d, %d)" % (width, height), lambda: self._reload(previous_image, dirty=True))

        self._reload(self.image.resize((width, height), resample=Image.BILINEAR), dirty=True)

    def crop(self, x1, y1, x2, y2):

        # capture state for rollback
        previous_image = self.image.copy()
        previous_layers = self.layers

        def do_rollback():
            self._reload(previous_image, dirty=True)
            for layer in previous_layers:
                layer.crop(-x1, -y1)

        self.history.snapshot("Cropping", do_rollback)

        self._reload(self.image.crop((x1, y1, x2, y2)), dirty=True)
        for layer in self.layers:
            layer.crop(x1, y1)

    def rotate(self, angle):
        self.history.snapshot("Rotation of %d°" % angle, lambda: self.rotate(-angle))
        self._reload(self.image.rotate(angle, expand=True), dirty=True)

    def flip_horizontal(self):
        self.history.snapshot("Horizontal flip", lambda: self.flip_horizontal())
        self._reload(self.image.transpose(Image.FLIP_LEFT_RIGHT), dirty=True)

    def flip_vertical(self):
        self.history.snapshot("Vertical flip", lambda: self.flip_vertical())
        self._reload(self.image.transpose(Image.FLIP_TOP_BOTTOM), dirty=True)

    def add_layer(self, layer):

        def when_layer_added():
            self.history.snapshot("Add %s" % layer.name, lambda: self.delete_layer(layer))
            self.dirty = True

        if not layer.transient:
            layer.connect("notify::dirty", lambda _, __: when_layer_added())

        self.layers.insert(0, layer)

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.ADD, layer)

    def index_of_layer(self, layer):
        for i, l in enumerate(self.layers):
            if l == layer:
                return i

    def delete_layer(self, layer, dirty=True):

        if dirty:
            self.dirty = True

        self.layers.remove(self.index_of_layer(layer))

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.DELETE, layer)

    def move_layer(self, layer, offset):
        if layer == None or offset == 0: return

        self.dirty = True

        index = self.index_of_layer(layer)
        new_index = (index + offset) % len(self.layers)

        self.layers.remove(index)
        self.layers.insert(new_index, layer)

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.MOVE, layer)

    def _update_layers_position(self):
        for i, l in enumerate(self.layers):
            l.position = i

    def get_previous_render(self):
        return self._previous_layer_render if self._previous_layer_render != None else self.image

    def get_layers_at_position(self, x, y):
        return [layer for layer in self.layers if layer.enabled and layer.hit_test(x, y)]

    def get_layers_positions_at_position(self, x, y):
        return [layer.position for layer in self.get_layers_at_position(x, y)]

    def draw(self, w, cr, mouse_x, mouse_y, helpers=False):

        # starting point is the image itself
        previous_back_layer = self.imageSurface
        self._previous_layer_render = pil_from_cairo_surface(self.imageSurface)
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # layers
        for layer in reversed(self.layers):

            # disabled layer won't render
            if not layer.enabled:
                continue

            # create intermediary surface
            layer_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.imageSurface.get_width(), self.imageSurface.get_height())
            layer_context = cairo.Context(layer_surface)

            # render previous layer
            layer_context.set_source_surface(previous_back_layer, 0, 0)
            layer_context.paint()

            # render layer
            layer_context.save()
            layer.draw(w, layer_context, mouse_x, mouse_y)
            layer_context.restore()

            # save intermediary render for the next layers
            previous_back_layer = layer_surface
            self._previous_layer_render = pil_from_cairo_surface(layer_surface)

            # render the layer helpers
            layer_context.save()
            if helpers:
                layer.draw_helpers(w, layer_context, mouse_x, mouse_y)
            layer_context.restore()

            # render the layer on top of the other ones
            cr.set_source_surface(layer_surface, 0, 0)
            cr.paint()

