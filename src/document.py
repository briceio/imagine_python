from PIL import Image
import cairo
from io import BytesIO
from gi.repository import Gtk, Gio, GObject, GdkPixbuf, GLib
import enum
import os
from .extensions import *

from .layers import Layer

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

    def __init__(self, path):
        GObject.GObject.__init__(self)
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

    def _reload(self, image):

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

    def rename(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.extension = os.path.splitext(path)[1]

    def resize(self, width, height):
        self.dirty = True
        self._reload(self.image.resize((width, height), resample=Image.BILINEAR))

    def crop(self, x1, y1, x2, y2):
        self.dirty = True
        self._reload(self.image.crop((x1, y1, x2, y2)))
        for layer in self.layers:
            layer.crop(x1, y1, x2, y2)

    def rotate(self, angle):
        self.dirty = True
        self._reload(self.image.rotate(angle, expand=True))

    def flip_horizontal(self):
        self.dirty = True
        self._reload(self.image.transpose(Image.FLIP_LEFT_RIGHT))

    def flip_vertical(self):
        self.dirty = True
        self._reload(self.image.transpose(Image.FLIP_TOP_BOTTOM))

    def add_layer(self, layer):
        self.dirty = True

        self.layers.insert(0, layer)

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.ADD, layer)

    def index_of_layer(self, layer):
        for i, l in enumerate(self.layers):
            if l == layer:
                return i

    def delete_layer(self, layer):
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

    def draw(self, w, cr, mouse_x, mouse_y, helpers=False):

        # starting point is the image itself
        previous_back_layer = self.imageSurface
        self._previous_layer_render = pil_from_cairo_surface(self.imageSurface)
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # layers
        for layer in reversed(self.layers):

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

