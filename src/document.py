from PIL import Image
import cairo
from io import BytesIO
from gi.repository import Gtk, Gio, GObject, GdkPixbuf, GLib
import enum
import os

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
    scale = GObject.Property(type=float, default=1.0)

    def __init__(self, path):
        GObject.GObject.__init__(self)
        self.path = path
        self.name = os.path.basename(path)
        self.image: Image = None
        self.thumbnail: GdkPixbuf = None
        self.imageSurface: cairo.ImageSurface = None
        self.layers = Gio.ListStore()
        self._reload(Image.open(path))

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
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        buffer.seek(0)

        self.imageSurface = cairo.ImageSurface.create_from_png(buffer)

    def resize(self, width, height):
        self._reload(self.image.resize((width, height), resample=Image.BILINEAR))
        # TODO resize the layers

    def crop(self, x1, y1, x2, y2):
        self._reload(self.image.crop((x1, y1, x2, y2)))
        for layer in self.layers:
            layer.crop(x1, y1, x2, y2)

    def rotate(self, angle):
        self._reload(self.image.rotate(angle, expand=True))
        # TODO rotate layers

    def flip_horizontal(self):
        self._reload(self.image.transpose(Image.FLIP_LEFT_RIGHT))
        # TODO flip layers

    def flip_vertical(self):
        self._reload(self.image.transpose(Image.FLIP_TOP_BOTTOM))
        # TODO flip layers

    def add_layer(self, layer):
        self.layers.insert(0, layer)

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.ADD, layer)

    def index_of_layer(self, layer):
        for i, l in enumerate(self.layers):
            if l == layer:
                return i

    def delete_layer(self, layer):
        self.layers.remove(self.index_of_layer(layer))

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.DELETE, layer)

    def move_layer(self, layer, offset):
        index = self.index_of_layer(layer)
        new_index = index + offset

        self.layers.remove(index)
        self.layers.insert(new_index, layer)

        self._update_layers_position()

        if self.on_updated_layers_list != None:
            self.on_updated_layers_list(LayerAction.MOVE, layer)

    def _update_layers_position(self):
        for i, l in enumerate(self.layers):
            l.position = i

    def draw(self, w, cr):

        # image itself
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # layers
        for layer in reversed(self.layers):
            layer.draw(w, cr)


