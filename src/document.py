from PIL import Image
import cairo
from io import BytesIO

class Document:

    image: Image
    imageSurface: cairo.ImageSurface

    def __init__(self, path):
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
        # TODO crop the layers

    def draw(self, w, cr):

        # image itself
        cr.set_source_surface(self.imageSurface, 0, 0)
        cr.paint()

        # TODO layers
        cr.set_source_rgb(1, 1, 0)
        cr.select_font_face("Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(40)
        cr.move_to(40, 40)
        cr.show_text("This is a test")


