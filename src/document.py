from PIL import Image
import cairo
from io import BytesIO
from gi.repository import Gtk, Gio, GObject


from .layers import Layer

class Document:

    # added layer callback
    on_added_layer = None

    def __init__(self, path):
        self.image: Image = None
        self.imageSurface: cairo.ImageSurface = None
        self.layers = Gio.ListStore()
        self._reload(Image.open(path))

    def _reload(self, image):
        self.image = image
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        buffer.seek(0)

        # create cairo surface
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

    def add_layer(self, layer):
        self.layers.append(layer)

        if self.on_added_layer != None:
            self.on_added_layer(layer)

    def draw(self, w, cr):

        # image itself
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # layers
        for layer in self.layers:
            layer.draw(w, cr)


