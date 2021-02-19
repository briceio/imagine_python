from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import cairo
import gi
import math
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Gio, GObject, Pango, PangoCairo

# common default tool widths
DEFAULT_WIDTH = 5

class Font(GObject.GObject):

    def __init__(self, desc):
        GObject.GObject.__init__(self)
        self.desc = desc

class Layer(GObject.GObject):

    name = GObject.Property(type=str, nick="Name")

    def __init__(self, name):
        GObject.GObject.__init__(self)
        self.name = name
        self.connect("notify", self.updated)

    def updated(self, obj, param):
        pass

    def get_tool(self):
        return None

    def draw(self, doc, w, cr):
        pass

    def crop(self, x1, y1, x2, y2):
        pass

class RectLayer(Layer):

    def __init__(self, name, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(name)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def crop(self, x1, y1, x2, y2):
        self.x1 -= x1
        self.y1 -= y1
        self.x2 -= x1
        self.y2 -= y1

class RectangleAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Rectangle", x1, x2, y1, y2)

    def get_tool(self):
        return "RectangleAnnotationTool"

    def draw(self, doc, w, cr):
        cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
        cr.set_line_width(0)
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.fill()

        cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.stroke()

class EllipsisAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")
    circle = GObject.Property(type=bool, default=False, nick="Circle")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0, circle = False):
        super().__init__("Ellipsis", x1, y1, x2, y2)
        self.circle = circle

    def get_tool(self):
        return "EllipsisAnnotationTool"

    def draw(self, doc, w, cr):

        def draw_ellipsis():
            width = self.x2 - self.x1
            height = self.y2 - self.y1
            ratio = width / height if height > 0 else 1
            cr.save()
            if not self.circle and width > 0 and ratio > 0:
                cr.translate(self.x1, self.y1)
                cr.scale(1, 1/ratio)
                cr.translate(-self.x1, -self.y1)
            cr.arc(self.x1, self.y1, width, 0, math.pi * 2)
            cr.restore()

        cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
        cr.set_line_width(0)
        draw_ellipsis()
        cr.fill()

        cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        draw_ellipsis()
        cr.stroke()

class LineAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")
    arrow = GObject.Property(type=bool, default=False, nick="Arrow")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0, arrow = False):
        super().__init__("Arrow" if arrow else "Line", x1, y1, x2, y2)
        self.arrow = arrow

    def get_tool(self):
        return "LineAnnotationTool"

    def draw(self, doc, w, cr):
        cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.move_to(self.x1, self.y1)
        cr.line_to(self.x2, self.y2)

        if self.arrow:
            arrow_length = 0
            arrow_angle = math.atan2(self.y2 - self.y1, self.x2 - self.x1)
            arrowhead_angle = math.pi/6
            arrowhead_length = 7 * self.width

            cr.rel_line_to(arrow_length * math.cos(arrow_angle), arrow_length * math.sin(arrow_angle))
            cr.rel_move_to(-arrowhead_length * math.cos(arrow_angle - arrowhead_angle), -arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
            cr.rel_line_to(arrowhead_length * math.cos(arrow_angle - arrowhead_angle), arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
            cr.rel_line_to(-arrowhead_length * math.cos(arrow_angle + arrowhead_angle), -arrowhead_length * math.sin(arrow_angle + arrowhead_angle))

        cr.stroke()

class TextAnnotationLayer(Layer):

    text = GObject.Property(type=str, default="Text", nick="Text", blurb="multiline")
    font = GObject.Property(type=Font, default=Font("Noto Sans Bold 30"), nick="Font")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")

    def __init__(self, x = 0, y = 0):
        super().__init__("Text")
        self.x = x
        self.y = y

    def get_tool(self):
        return "TextAnnotationTool"

    def crop(self, x1, y1, x2, y2):
        self.x -= x1
        self.y -= y1

    def draw(self, doc, w, cr):
        cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
        cr.move_to(self.x, self.y)

        desc = Pango.font_description_from_string(self.font.desc)

        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(desc)
        layout.set_text(self.text, -1)
        PangoCairo.show_layout(cr, layout)
        
class LightingLayer(RectLayer):

    brightness = GObject.Property(type=float, default=1.5, nick="Brightness")
    contrast = GObject.Property(type=float, default=1.0, nick="Contrast")
    sharpness = GObject.Property(type=float, default=1.0, nick="Sharpness")
    color = GObject.Property(type=float, default=1.0, nick="Color")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Lighting", x1, y1, x2, y2)
        self._image_surface = None
        self.updating = False

    def get_tool(self):
        return "LightingTool"

    def updated(self, obj, param):
        self.updating = True

    def draw(self, doc, w, cr):

        if self.x2 - self.x1 == 0 or self.y2 - self.y1 == 0:
            return

        if self._image_surface == None or self.updating:

            # crop the image
            rect_image = doc.image.crop((self.x1, self.y1, self.x2, self.y2))

            # enhance it
            rect_image = ImageEnhance.Brightness(rect_image).enhance(self.brightness)
            rect_image = ImageEnhance.Contrast(rect_image).enhance(self.contrast)
            rect_image = ImageEnhance.Sharpness(rect_image).enhance(self.sharpness)
            rect_image = ImageEnhance.Color(rect_image).enhance(self.color)

            # convert it to surface
            buffer = BytesIO()
            rect_image.save(buffer, format="PNG")
            buffer.seek(0)
            self._image_surface = cairo.ImageSurface.create_from_png(buffer)

            self.updating = False

        # draw it
        cr.set_source_surface(self._image_surface, self.x1, self.y1)
        cr.paint()

class BlurLayer(RectLayer):

    box = GObject.Property(type=float, default=0.0, nick="Box Blur")
    gaussian = GObject.Property(type=float, default=10.0, nick="Gaussian Blur")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Blur", x1, y1, x2, y2)
        self._image_surface = None
        self.updating = False

    def get_tool(self):
        return "BlurTool"

    def updated(self, obj, param):
        self.updating = True

    def draw(self, doc, w, cr):

        if self.x2 - self.x1 == 0 or self.y2 - self.y1 == 0:
            return

        if self._image_surface == None or self.updating:

            # crop the image
            rect_image = doc.image.crop((self.x1, self.y1, self.x2, self.y2))

            # enhance it
            rect_image = rect_image.filter(ImageFilter.BoxBlur(self.box))
            rect_image = rect_image.filter(ImageFilter.GaussianBlur(self.gaussian))

            # convert it to surface
            buffer = BytesIO()
            rect_image.save(buffer, format="PNG")
            buffer.seek(0)
            self._image_surface = cairo.ImageSurface.create_from_png(buffer)

            self.updating = False

        # draw it
        cr.set_source_surface(self._image_surface, self.x1, self.y1)
        cr.paint()
