from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import cairo
import gi
import math
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Gio, GObject, Pango, PangoCairo
import emojis
from .extensions import *

# common default tool widths
DEFAULT_WIDTH = 5

class Font(GObject.GObject):

    def __init__(self, desc):
        GObject.GObject.__init__(self)
        self.desc = desc

class Selector(GObject.GObject):

    def __init__(self, options, index=0):
        GObject.GObject.__init__(self)
        self.options = options
        self.index = index

    def value(self):
        return self.options[self.index]

class Layer(GObject.GObject):

    name = GObject.Property(type=str, nick="Name")
    position = GObject.Property(type=int, default=-1)

    def __init__(self, document, name):
        GObject.GObject.__init__(self)
        self.document = document
        self.name = name
        self.connect("notify", self.updated)

        # offset (if explicitly moved)
        self.offset_x = 0
        self.offset_y = 0

    def updated(self, obj, param):
        pass

    def get_tool(self):
        return None

    def draw(self, w, cr):
        cr.translate(self.offset_x, self.offset_y)

    def crop(self, x1, y1, x2, y2):
        pass

    def is_first_layer(self):
        return self.position == 0

    def is_last_layer(self):
        return self.position == len(self.document.layers) - 1

class RectLayer(Layer):

    def __init__(self, document, name, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, name)

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def crop(self, x1, y1, x2, y2):
        self.x1 -= x1
        self.y1 -= y1
        self.x2 -= x1
        self.y2 -= y1

class PointLayer(Layer):

    def __init__(self, document, name, x = 0, y = 0):
        super().__init__(document, name)

        self.x = x
        self.y = y

    def crop(self, x1, y1, x2, y2):
        self.x -= x1
        self.y -= y1

class RectangleAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width", minimum=0, maximum=50)
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, "Rectangle", x1, x2, y1, y2)

    def get_tool(self):
        return "RectangleAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

        cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
        cr.set_line_width(0)
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.fill_preserve()

        cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.stroke()

class EllipseAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width", minimum=0, maximum=50)
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0, circle = False):
        super().__init__(document, "Circle" if circle else "Ellipse", x1, y1, x2, y2)
        self.circle = circle

    def get_tool(self):
        return "EllipseAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

        def draw():
            cr.save()
            if self.circle:
                draw_circle()
            else:
                draw_ellipse()
            cr.restore()

        def draw_ellipse():
            width = self.x2 - self.x1
            height = self.y2 - self.y1
            if width != 0 and height != 0:
                center_x = self.x1 + width / 2
                center_y = self.y1 + height / 2
                radius = math.sqrt(pow(width, 2) + pow(height, 2))

                cr.translate(center_x, center_y)
                cr.scale(width / 2.0, height / 2.0)
                cr.arc(0.0, 0.0, 1.0, 0.0, 2.0 * math.pi)

        def draw_circle():
            width = abs(self.x2 - self.x1)
            height = abs(self.y2 - self.y1)
            ratio = width / height if height != 0 else 1
            cr.arc(self.x1, self.y1, width, 0, math.pi * 2)

        cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
        cr.set_line_width(0)
        draw()
        cr.fill_preserve()

        cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.stroke()

class LineAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width", minimum=1, maximum=50)
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")
    arrow = GObject.Property(type=bool, default=False, nick="Arrow")

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0, arrow = False):
        super().__init__(document, "Arrow" if arrow else "Line", x1, y1, x2, y2)
        self.arrow = arrow

    def get_tool(self):
        return "LineAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

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

class TextAnnotationLayer(PointLayer):

    text = GObject.Property(type=str, default="Text", nick="Text", blurb="multiline")
    font = GObject.Property(type=Font, default=Font("Noto Sans Bold 30"), nick="Font")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")
    centered = GObject.Property(type=bool, default=True, nick="Center")

    def __init__(self, document, x = 0, y = 0):
        super().__init__(document, "Text")

    def get_tool(self):
        return "TextAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

        # map GTK font description to Pango
        desc = Pango.font_description_from_string(self.font.desc)

        # layout options
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(desc)
        layout.set_alignment(Pango.Alignment.CENTER if self.centered else Pango.Alignment.LEFT)
        layout.set_text(self.text, -1)

        # font options
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_DEFAULT) # ANTIALIAS_SUBPIXEL
        PangoCairo.context_set_font_options(layout.get_context(), fo)

        # center or not
        width, height = layout.get_pixel_size()
        if self.centered:
            cr.translate(self.x - width / 2, self.y - height / 2)
        else:
            cr.translate(self.x, self.y)

        # render
        cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
        PangoCairo.show_layout(cr, layout)
        
Selector.FULL_EMOJI_SELECTOR = Selector(emojis.db.get_emoji_aliases().values()) # TODO bug perf use iter() instead of dict in Selector
Selector.SMALL_EMOJI_SELECTOR = Selector([
    "😀", "😁", "😂", "😄", "😅", "😆", "😇", "😉", "😊", "😋",
    "😍", "🤩", "😎", "😑", "😜", "😝", "😡", "🤬", "😖", "😤",
    "😥", "😧", "😨", "😰", "😱", "😲", "😳", "😵", "😶", "😬",
    "😵", "😵", "😷", "🙃", "🙄", "🤤", "🤧", "🤪", "🤐", "🤕",
    "😢", "🤯", "🤢", "🤤", "🧐", "🤘", "🤟", "🤙", "🤝", "🤞",
    "🙈", "🙉", "🙊", "🧚", "🧜", "🌹", "🌺", "🌸", "🌷", "🌼",
    "🐄", "🐖", "🐽", "🍆", "🌽", "🍌", "🥕", "🥖", "🍑", "🍒", "🥩", "🍖", "🍗", "🥚",
    "🍡", "🍢", "🍣", "🍤", "🍥", "🍭", "🍬", "🍩", "🍳", "🍴",
    "🍷", "🍸", "🍹", "🍺", "🍻", "🍾", "🍿", "🥂", "🍼", "🔪",
    "🥄", "🎀", "🎁", "🃏", "🎆", "🎇", "🎈", "🎉", "🎊", "🎋",
    "🎯", "🏅", "🏆", "🥊", "🥇", "🥈", "🥉", "🥋", "🔥", "⚡", "⭐", "🌟", "💡"
    "🌀", "☔", "⚓", "⏳", "⌚", "🌈", "🌋", "🌊", "🌞", "🌜",
    "🎠", "🏡", "🎰", "🎭", "🎨", "💒", "🎶", "🎺", "🏹", "💉",
    "💊", "💰", "📌", "📍", "📎", "📏", "📈", "📞", "📢", "📣",
    "📡", "📫", "📺", "🔍", "🔎", "🔒", "🔑", "🔋", "🔌", "✅",
    "⛔", "❌", "❎", "❓", "❗", "➕", "➖", "⭕", "🆘", "🆙",
    "🆗", "🆔", "🆒", "💯", "🔙", "🔟", "🔆", "🔴", "🔵", "🏁",
    "🏴", "🚩"
])

class EmojiAnnotationLayer(PointLayer):

    size = GObject.Property(type=int, default=150, nick="Size", minimum=1, maximum=1000)
    emoji = GObject.Property(type=Selector, default=Selector.SMALL_EMOJI_SELECTOR, nick="Emoji")

    def __init__(self, document, x = 0, y = 0):
        super().__init__(document, "Emoji")

    def get_tool(self):
        return "EmojiAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

        # prepare font
        desc = Pango.font_description_from_string("Noto Sans Bold")
        desc.set_absolute_size(Pango.SCALE * self.size)

        # layout options
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(desc)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(self.emoji.value(), -1)

        # font options
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_DEFAULT)
        PangoCairo.context_set_font_options(layout.get_context(), fo)

        # center
        width, height = layout.get_pixel_size()
        cr.translate(self.x - width / 2, self.y - height / 2)

        # render on surface to apply alpha
        cr.set_source_rgba(1, 1, 1, 1)
        PangoCairo.show_layout(cr, layout)

class LightingLayer(RectLayer):

    brightness = GObject.Property(type=float, default=1.5, nick="Brightness", minimum=0.0, maximum=10.0)
    contrast = GObject.Property(type=float, default=1.0, nick="Contrast", minimum=0.0, maximum=10.0)
    sharpness = GObject.Property(type=float, default=1.0, nick="Sharpness", minimum=0.0, maximum=10.0)
    color = GObject.Property(type=float, default=1.0, nick="Color", minimum=0.0, maximum=10.0)

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, "Lighting", x1, y1, x2, y2)
        self._image_surface = None
        self._image = None
        self.updating = False
        self.enhancing = False

    def get_tool(self):
        return "LightingTool"

    def updated(self, obj, param):
        self.enhancing = True

    def draw(self, w, cr):
        super().draw(w, cr)

        x1, y1, x2, y2 = normalize_rect(self.x1, self.y1, self.x2, self.y2)

        if x2 - x1 <= 0 or y2 - y1 <= 0:
            return

        def enhance():
            image = ImageEnhance.Brightness(self._image).enhance(self.brightness)
            image = ImageEnhance.Contrast(image).enhance(self.contrast)
            image = ImageEnhance.Sharpness(image).enhance(self.sharpness)
            image = ImageEnhance.Color(image).enhance(self.color)

            self._image_surface = cario_image_from_pil(image)

            self.enhancing = False

        if self._image == None or self.updating:
            self._image = self.document.get_previous_render().crop((x1 + self.offset_x, y1 + self.offset_y, x2 + self.offset_x, y2 + self.offset_y))
            enhance()
            self.updating = False

        if not self._image_surface == None and self.enhancing:
            enhance()

        # draw it
        cr.set_source_surface(self._image_surface, x1, y1)
        cr.paint()

class BlurLayer(RectLayer):

    box = GObject.Property(type=float, default=0.0, nick="Box Blur", minimum=0.0, maximum=10.0)
    gaussian = GObject.Property(type=float, default=10.0, nick="Gaussian Blur", minimum=0.0, maximum=10.0)

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, "Blur", x1, y1, x2, y2)
        self._image_surface = None
        self._image = None
        self.updating = False
        self.enhancing = False

    def get_tool(self):
        return "BlurTool"

    def updated(self, obj, param):
        self.enhancing = True

    def draw(self, w, cr):
        super().draw(w, cr)

        x1, y1, x2, y2 = normalize_rect(self.x1, self.y1, self.x2, self.y2)

        if x2 - x1 <= 0 or y2 - y1 <= 0:
            return

        def enhance():
            image = self._image.filter(ImageFilter.BoxBlur(self.box))
            image = image.filter(ImageFilter.GaussianBlur(self.gaussian))

            self._image_surface = cario_image_from_pil(image)

            self.enhancing = False

        if self._image == None or self.updating:
            self._image = self.document.get_previous_render().crop((x1 + self.offset_x, y1 + self.offset_y, x2 + self.offset_x, y2 + self.offset_y))
            enhance()
            self.updating = False

        if not self._image_surface == None and self.enhancing:
            enhance()

        # draw it
        cr.set_source_surface(self._image_surface, x1, y1)
        cr.paint()

class ZoomAnnotationLayer(RectLayer):

    AUTO_FRAME_OFFSET = (-20, -20)

    zoom = GObject.Property(type=float, default=2, nick="Zoom", minimum=1.0, maximum=10.0)
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")
    frame = GObject.Property(type=bool, default=True, nick="Frame")
    frame_width = GObject.Property(type=int, default=3, nick="Frame Width", minimum=1, maximum=10)
    shadow = GObject.Property(type=bool, default=True, nick="Shadow")
    shadow_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(0, 0, 0, 1), nick="Shadow Color")
    shadow_extend = GObject.Property(type=int, default=15, nick="Shadow Extend", minimum=0, maximum=100)

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, "Zoom")
        self._image_surface = None
        self.frame_x = 0
        self.frame_y = 0
        self.frame_position_forced = False

    def get_tool(self):
        return "ZoomAnnotationTool"

    def updated(self, obj, param):
        self.update()

    def clear(self):
        self._image_surface = None

    def update(self):
        if self.x2 - self.x1 == 0 or self.y2 - self.y1 == 0:
            return

        image = self.document.get_previous_render().crop((self.x1 + self.offset_x, self.y1 + self.offset_y, self.x2 + self.offset_x, self.y2 + self.offset_y))
        self._image_surface = cario_image_from_pil(image)

        if not self.frame_position_forced:
            self.frame_x = self.x1 + ((self.x2 - self.x1) / 2)
            self.frame_y = self.y1 + ((self.y2 - self.y1) / 2)

    def draw(self, w, cr):
        super().draw(w, cr)

        if self._image_surface != None:

            # computation
            source_x = self.x1
            source_y = self.y1
            source_width = self.x2 - self.x1
            source_height = self.y2 - self.y1
            target_width = (self.x2 - self.x1) * self.zoom
            target_height = (self.y2 - self.y1) * self.zoom
            offset_x = self.AUTO_FRAME_OFFSET[0] if not self.frame_position_forced else -target_width / 2
            offset_y = self.AUTO_FRAME_OFFSET[1] if not self.frame_position_forced else -target_height / 2
            target_frame_x = self.frame_x + offset_x
            target_frame_y = self.frame_y + offset_y

            if self.shadow:
                r = self.shadow_color.red
                g = self.shadow_color.green
                b = self.shadow_color.blue

                # bottom shadow
                shadow_gradient = cairo.LinearGradient(0, target_frame_y + target_height, 0, target_frame_y + target_height + self.shadow_extend)
                shadow_gradient.add_color_stop_rgba(0, r, g, b, 1)
                shadow_gradient.add_color_stop_rgba(1, r, g, b, 0)
                cr.rectangle(target_frame_x + self.shadow_extend, target_frame_y + target_height, target_width - self.shadow_extend, self.shadow_extend)
                cr.set_source(shadow_gradient)
                cr.fill()

                # right shadow
                shadow_gradient = cairo.LinearGradient(target_frame_x + target_width, 0, target_frame_x + target_width + self.shadow_extend, 0)
                shadow_gradient.add_color_stop_rgba(0, r, g, b, 1)
                shadow_gradient.add_color_stop_rgba(1, r, g, b, 0)
                cr.rectangle(target_frame_x + target_width, target_frame_y + self.shadow_extend, self.shadow_extend, target_height - self.shadow_extend)
                cr.set_source(shadow_gradient)
                cr.fill()

                # corner shadow
                shadow_gradient = cairo.RadialGradient(target_frame_x + target_width, target_frame_y + target_height, 0, target_frame_x + target_width, target_frame_y + target_height, self.shadow_extend)
                shadow_gradient.add_color_stop_rgba(0, r, g, b, 1)
                shadow_gradient.add_color_stop_rgba(1, r, g, b, 0)
                cr.rectangle(target_frame_x + target_width, target_frame_y + target_height, self.shadow_extend, self.shadow_extend)
                cr.set_source(shadow_gradient)
                cr.fill()

            # source frame
            if self.frame:
                cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
                cr.set_line_width(self.frame_width)
                cr.set_dash([])
                cr.rectangle(source_x, source_y, source_width, source_height)
                cr.stroke()

                # source to target frame effect
                cr.set_dash([self.frame_width * 2, self.frame_width * 2])
                cr.move_to(source_x, source_y)
                cr.line_to(target_frame_x, target_frame_y)
                cr.move_to(source_x + source_width, source_y)
                cr.line_to(target_frame_x + target_width, target_frame_y)
                cr.move_to(source_x + source_width, source_y + source_height)
                cr.line_to(target_frame_x + target_width, target_frame_y + target_height)
                cr.move_to(source_x, source_y + source_height)
                cr.line_to(target_frame_x, target_frame_y + target_height)
                cr.stroke()

            # zoomed image
            cr.save()
            cr.translate(self.frame_x + offset_x, self.frame_y + offset_y)
            cr.scale(self.zoom, self.zoom)
            cr.set_source_surface(self._image_surface, 0, 0)
            cr.paint()
            cr.restore()

            # target frame
            if self.frame:
                cr.set_dash([])
                cr.rectangle(target_frame_x, target_frame_y, target_width, target_height)
                cr.stroke()

class PathAnnotationLayer(Layer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width", minimum=0, maximum=50)
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")
    dashed = GObject.Property(type=bool, default=False, nick="Dashed")
    closed = GObject.Property(type=bool, default=False, nick="Closed")

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__(document, "Path")

        self.points = []

    def get_tool(self):
        return "PathAnnotationTool"

    def draw(self, w, cr):
        super().draw(w, cr)

        if len(self.points) > 1:
            cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)

            cr.new_path()
            cr.move_to(self.points[0][0], self.points[0][1])
            for x, y in self.points:
                cr.line_to(x, y)

            if self.closed:
                cr.close_path()

            cr.fill_preserve()

            cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
            if self.dashed:
                cr.set_dash([self.width, self.width])
            cr.set_line_width(self.width)

            cr.stroke()

class ImageAnnotationLayer(RectLayer):

    path = GObject.Property(type=str, nick="Path", blurb="file")
    keep_aspect = GObject.Property(type=bool, default=True, nick="Keep Aspect")
    alpha = GObject.Property(type=float, default=1.0, nick="Alpha", minimum=0.0, maximum=1.0)

    def __init__(self, document, x1 = 0, y1 = 0, x2 = 0, y2 = 0, path=None):
        super().__init__(document, "Image", x1, y1, x2, y2)

        self.path = path
        self._image_surface = None

        if self.path != None:
            self._reload_image()

    def get_tool(self):
        return "ImageAnnotationTool"

    def updated(self, obj, param):
        super().updated(obj, param)

        if param.name == "path":
            self._reload_image()

    def _reload_image(self):
        if self.path != None:
            self._image_surface = cario_image_from_pil(Image.open(self.path))
        else:
            self._image = None

    def ask_for_image_if_needed(self):
        if self.path == None:
            win = Gdk.Screen.get_active_window(Gdk.Screen.get_default())

            dialog = Gtk.FileChooserDialog("Image to insert", win, Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
            dialog.set_transient_for(win) # link dialog to parent

            filter = Gtk.FileFilter()
            filter.set_name("Images")
            filter.add_pattern("*.png")
            filter.add_pattern("*.jpg")
            filter.add_pattern("*.jpeg")
            dialog.add_filter(filter)

            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                self.path = dialog.get_filename()
                self._reload_image()

            dialog.destroy()

    def draw(self, w, cr):
        super().draw(w, cr)

        if self._image_surface == None:
            cr.set_source_rgba(1, 1, 1, 0.75)
            cr.set_line_width(DEFAULT_WIDTH)
            cr.set_dash([10, 10])
            cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
            cr.stroke()
        else:
            source_w = self._image_surface.get_width()
            source_h = self._image_surface.get_height()
            target_w = self.x2 - self.x1
            target_h = self.y2 - self.y1
            scale_x = 1.0
            scale_y = 1.0

            if target_w != 0 and target_h != 0:
                if self.keep_aspect:
                    source_ratio = source_w / source_h
                    target_ratio = target_w / target_h

                    if source_ratio >= target_ratio:
                        scale_x = target_w / source_w
                        scale_y = scale_x
                    else:
                        scale_y = target_h / source_h
                        scale_x = scale_y
                else:
                    scale_x = target_w / source_w
                    scale_y = target_h / source_h

                cr.save()
                cr.translate(self.x1, self.y1)
                cr.scale(scale_x, scale_y)
                cr.set_source_surface(self._image_surface, 0, 0)
                cr.paint_with_alpha(self.alpha)
                cr.restore()

