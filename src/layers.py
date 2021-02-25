from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import cairo
import gi
import math
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Gio, GObject, Pango, PangoCairo
import emojis
from .extensions import *
import copy

# common default tool widths
DEFAULT_WIDTH = 5

class Anchor:

    ANCHOR_COLOR = (1, 1, 1, 1)
    ANCHOR_WIDTH = 2
    ANCHOR_RADIUS = 7
    ANCHOR_OPERATOR = cairo.OPERATOR_OVER

    def __init__(self, x=None, y=None):
        self.set(x, y)

        # visible flag
        self.visible = True

        # linked anchors
        self.linked_anchors = {}

        self._grabbed = False

    def set(self, x, y):
        self.x = x
        self.y = y

    def add(self, x, y):
        self.x += x
        self.y += y

    def valid(self):
        return self.x != None and self.y != None

    def link(self, anchor):
        self.linked_anchors[anchor] = None

    def hit_test(self, x, y):
        return self.within(x, y, 10)

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1 and self.within(mouse_x, mouse_y, 10):
            self._grabbed = True
            self.set(mouse_x, mouse_y)

            # linked anchors
            for anchor in self.linked_anchors:
                self.linked_anchors[anchor] = (anchor.x - self.x, anchor.y - self.y)

            return True

        return False


    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1 and self._grabbed:
            self._grabbed = False
            self.set(mouse_x, mouse_y)

    def mouse_move(self, w, cr, mouse_x, mouse_y):
        if self._grabbed:
            self.set(mouse_x, mouse_y)

            # linked anchors
            for anchor in self.linked_anchors:
                offset_x, offset_y = self.linked_anchors[anchor]
                anchor.x = self.x + offset_x
                anchor.y = self.y + offset_y

    def within(self, x, y, precision=0):
        if self.visible and self.valid():
            distance = math.sqrt((x - self.x)**2 + (y - self.y)**2)
            return distance <= (Anchor.ANCHOR_RADIUS + precision)
        return False

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        if self.visible and self.valid():
            cr.save()

            scale = 1 / (doc.scale / 100)
            radius = Anchor.ANCHOR_RADIUS * scale

            cr.set_source_rgba(Anchor.ANCHOR_COLOR[0], Anchor.ANCHOR_COLOR[1], Anchor.ANCHOR_COLOR[2], Anchor.ANCHOR_COLOR[3])
            cr.set_operator(Anchor.ANCHOR_OPERATOR);
            cr.set_line_width(Anchor.ANCHOR_WIDTH * scale)
            cr.arc(self.x, self.y, radius, 0, math.pi * 2)
            cr.fill()

            cr.restore()

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

    # keys modifiers
    KEY_CONTROL = False
    KEY_SHIFT = False
    KEY_ALT = False

    # name of the layer
    name = GObject.Property(type=str, nick="Name", blurb="order=0")

    # is the layer enabled?
    enabled = GObject.Property(type=bool, default=True, nick="Enabled", blurb="order=1")

    # position of the layer in the stack
    position = GObject.Property(type=int, default=-1)

    # is the layer active?
    active = GObject.Property(type=bool, default=False)

    def __init__(self, document, name, reticule=False, draw_anchors=True):
        GObject.GObject.__init__(self)

        self.document = document
        self.name = name
        self.dirty = True
        self.reticule = reticule
        self.draw_anchors = draw_anchors
        self.connect("notify", self.updated)

        # anchors
        self.anchors = []

    def _add_anchor(self, x=None, y=None):
        anchor = Anchor(x, y)
        self.anchors.append(anchor)
        return anchor

    def _remove_anchor(self, anchor):
        self.anchors.remove(anchor)

    def hit_test(self, x, y):
        hit = False
        for anchor in self.anchors:
            if anchor.hit_test(x, y):
                hit = True
                break

        return hit

    # static key handler to process custom keys
    def on_key(widget, event):
        Layer.KEY_CONTROL = (event.keyval == Gdk.KEY_Control_L or event.keyval == Gdk.KEY_Control_R) and event.type == Gdk.EventType.KEY_PRESS
        Layer.KEY_SHIFT = (event.keyval == Gdk.KEY_Shift_L or event.keyval == Gdk.KEY_Shift_R) and event.type == Gdk.EventType.KEY_PRESS
        Layer.KEY_ALT = (event.keyval == Gdk.KEY_Alt_L or event.keyval == Gdk.KEY_Alt_R) and event.type == Gdk.EventType.KEY_PRESS

    def updated(self, obj, param):
        pass

    def draw(self, w, cr, mouse_x, mouse_y):
        pass

    def draw_helpers(self, w, cr, mouse_x, mouse_y):
        from .window import ImagineWindow

        if self.active:

            # reticule
            if ImagineWindow.USER_SETTINGS.get_boolean("display-reticule") and self.reticule:
                cr.set_source_rgba(1, 1, 1, 0.7)
                cr.set_dash([10, 10])
                cr.set_line_width(1)

                cr.move_to(mouse_x, 0)
                cr.line_to(mouse_x, self.document.imageSurface.get_height())

                cr.move_to(0, mouse_y)
                cr.line_to(self.document.imageSurface.get_width(), mouse_y)

                cr.stroke()

            # anchors
            if self.draw_anchors:
                for anchor in self.anchors:
                    anchor.draw(self.document, w, cr, mouse_x, mouse_y)

    def crop(self, x1, y1, x2, y2):
        pass

    def valid(self):
        return True

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):

        # anchors
        handled = False
        for anchor in self.anchors:
            if anchor.mouse_down(w, cr, mouse_x, mouse_y, mouse_button) and not handled:
                handled = True

        return handled

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):

        # anchors
        for anchor in self.anchors:
            anchor.mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

    def mouse_move(self, w, cr, mouse_x, mouse_y):

        # anchors
        for anchor in self.anchors:
            anchor.mouse_move(w, cr, mouse_x, mouse_y)

    def is_first_layer(self):
        return self.position == 0

    def is_last_layer(self):
        return self.position == len(self.document.layers) - 1

class RectLayer(Layer):

    RECT_TYPE_NONE = 0
    RECT_TYPE_CLASSIC = 1
    RECT_TYPE_CONTRAST = 1

    def __init__(self, document, name, rect=RECT_TYPE_NONE, persistent_rect=False, draw_anchors=True):
        super().__init__(document, name, reticule=True, draw_anchors=draw_anchors)

        # anchors
        self.anchor1 = self._add_anchor()
        self.anchor2 = self._add_anchor()

        self.rect = rect
        self.persistent_rect = persistent_rect

        # initialization
        self._init = False

        # move between anchors
        self._moving = None
        self._moving_anchor1 = None
        self._moving_anchor1 = None

    def hit_test(self, x, y):
        hit = super().hit_test(x, y)

        if not hit:
            hit = self.between_anchors(x, y)

        return hit

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):
        handled = super().mouse_down(w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if not handled and mouse_button == 1:
            if self.dirty:
                self._init = True
                self.anchor1.set(mouse_x, mouse_y)
                handled = True
            elif self.between_anchors(mouse_x, mouse_y):
                self._moving = (mouse_x, mouse_y)
                self._moving_anchor1 = copy.deepcopy(self.anchor1)
                self._moving_anchor2 = copy.deepcopy(self.anchor2)
                handled = True
            elif not self.on_anchors(mouse_x, mouse_y) and Layer.KEY_CONTROL:
                self._init = True
                self.dirty = True
                self.anchor1.set(mouse_x, mouse_y)
                handled = True

        return handled

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            if self._init:
                self.dirty = False
                self._init = False
                self.anchor2.set(mouse_x, mouse_y)
            elif self._moving != None:
                self._moving = None

    def mouse_move(self, w, cr, mouse_x, mouse_y):
        super().mouse_move(w, cr, mouse_x, mouse_y)

        if self._init:
            self.anchor2.set(mouse_x, mouse_y)
        elif self._moving != None:
            delta_x = mouse_x - self._moving[0]
            delta_y = mouse_y - self._moving[1]
            self.anchor1.set(self._moving_anchor1.x + delta_x, self._moving_anchor1.y + delta_y)
            self.anchor2.set(self._moving_anchor2.x + delta_x, self._moving_anchor2.y + delta_y)

    def valid(self):
        return self.anchor1 != None and self.anchor2 != None and self.anchor1.valid() and self.anchor2.valid()

    def on_anchors(self, x, y):
        return self.anchor1.within(x, y, 10) or self.anchor2.within(x, y, 10)

    def between_anchors(self, x, y):
        if self.valid():
            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)
            if ok:
                return not self.on_anchors(x, y) and x >= x1 and x <= x2 and y >= y1 and y <= y2
        return False

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        # rect
        if self.rect != RectLayer.RECT_TYPE_NONE and (self.persistent_rect or not self.dirty) and self.valid():
            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:
                width = self.document.imageSurface.get_width()
                height = self.document.imageSurface.get_height()

                if self.rect == RectLayer.RECT_TYPE_CLASSIC:
                    scale = 1 / (self.document.scale / 100)

                    cr.set_source_rgba(Anchor.ANCHOR_COLOR[0], Anchor.ANCHOR_COLOR[1], Anchor.ANCHOR_COLOR[2], Anchor.ANCHOR_COLOR[3])
                    cr.set_operator(Anchor.ANCHOR_OPERATOR);
                    cr.set_line_width(Anchor.ANCHOR_WIDTH * scale)

                    cr.set_dash([Anchor.ANCHOR_WIDTH * scale * 5, Anchor.ANCHOR_WIDTH * scale * 5])
                    cr.rectangle(x1, y1, x2 - x1, y2 - y1)
                    cr.stroke()
                elif self.rect == RectLayer.RECT_TYPE_CONTRAST:
                    cr.set_source_rgba(0, 0, 0, 0.5)
                    cr.set_line_width(0)
                    cr.set_dash([])
                    cr.rectangle(0, 0, width, y1)
                    cr.rectangle(0, 0, x1, height)
                    cr.rectangle(x2, 0, width - x2, height)
                    cr.rectangle(0, y2, width, height - y2)
                    cr.fill()

    def crop(self, x1, y1, x2, y2):
         self.anchor1.x -= x1
         self.anchor1.y -= y1
         self.anchor2.x -= x1
         self.anchor2.y -= y1

class PointLayer(Layer):

    def __init__(self, document, name, draw_anchors=True):
        super().__init__(document, name, reticule=True, draw_anchors=draw_anchors)

        # anchor
        self.anchor = self._add_anchor()

        # initial position
        self._moving = False

    def valid(self):
        return self.anchor != None and self.anchor.valid()

    def crop(self, x1, y1, x2, y2):
         self.anchor.x -= x1
         self.anchor.y -= y1

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):
        handled = super().mouse_down(w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if not handled and mouse_button == 1 and (self.dirty or Layer.KEY_CONTROL):
            self._moving = True
            self.anchor.set(mouse_x, mouse_y)
            handled = True

        return handled

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self._moving:
            self.dirty = False
            self._moving = False
            self.anchor.set(mouse_x, mouse_y)

    def mouse_move(self, w, cr, mouse_x, mouse_y):
        super().mouse_move(w, cr, mouse_x, mouse_y)

        if self._moving:
            self.anchor.set(mouse_x, mouse_y)

    def valid(self):
        return self.anchor != None and self.anchor.valid()

class CropLayer(RectLayer):

    def __init__(self, document):
        super().__init__(document, "Crop", rect=RectLayer.RECT_TYPE_CONTRAST, draw_anchors=False)

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self.valid():
            x1, y1, x2, y2 = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if x2 - x1 <= 0 or y2 - y1 <= 0:
                return

            self.document.crop(x1, y1, x2, y2)

class RectangleAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Stroke Width", minimum=0, maximum=50, blurb="order=4")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color", blurb="order=3")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color", blurb="order=2")

    def __init__(self, document):
        super().__init__(document, "Rectangle")

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():
            cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
            cr.set_line_width(0)
            cr.rectangle(self.anchor1.x, self.anchor1.y, self.anchor2.x - self.anchor1.x, self.anchor2.y - self.anchor1.y)
            cr.fill_preserve()

            cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
            cr.set_line_width(self.width)
            cr.set_dash([])
            cr.stroke()

class CircleAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Stroke Width", minimum=0, maximum=50, blurb="order=4")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color", blurb="order=3")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color", blurb="order=2")

    def __init__(self, document):
        super().__init__(document, "Circle")

        # link both anchors
        self.anchor1.link(self.anchor2)

    def between_anchors(self, x, y):
        if self.valid() and not self.on_anchors(x, y):
            radius = math.sqrt((self.anchor2.x - self.anchor1.x)**2 + (self.anchor2.y - self.anchor1.y)**2)
            distance = math.sqrt((self.anchor1.x - x)**2 + (self.anchor1.y - y)**2)
            return distance <= radius
        return False

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        def draw():
            cr.save()

            radius = math.sqrt((self.anchor2.x - self.anchor1.x)**2 + (self.anchor2.y - self.anchor1.y)**2)
            cr.arc(self.anchor1.x, self.anchor1.y, radius, 0, math.pi * 2)

            cr.restore()

        if self.valid():
            cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
            cr.set_line_width(0)
            draw()
            cr.fill_preserve()

            cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
            cr.set_line_width(self.width)
            cr.set_dash([])
            cr.stroke()

class EllipseAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Stroke Width", minimum=0, maximum=50, blurb="order=4")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color", blurb="order=3")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color", blurb="order=2")

    def __init__(self, document):
        super().__init__(document, "Ellipse", rect=RectLayer.RECT_TYPE_CLASSIC, persistent_rect=True)

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        def draw():
            cr.save()

            width = self.anchor2.x - self.anchor1.x
            height = self.anchor2.y - self.anchor1.y

            if width != 0 and height != 0:
                center_x = self.anchor1.x + width / 2
                center_y = self.anchor1.y + height / 2
                radius = math.sqrt(pow(width, 2) + pow(height, 2))

                cr.translate(center_x, center_y)
                cr.scale(width / 2.0, height / 2.0)
                cr.arc(0.0, 0.0, 1.0, 0.0, 2.0 * math.pi)

            cr.restore()

        if self.valid():
            cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
            cr.set_line_width(0)
            draw()
            cr.fill_preserve()

            cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
            cr.set_line_width(self.width)
            cr.set_dash([])
            cr.stroke()

class LineAnnotationLayer(RectLayer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width", minimum=1, maximum=50, blurb="order=3")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color", blurb="order=2")
    arrow = GObject.Property(type=bool, default=False, nick="Arrow", blurb="order=4")

    def __init__(self, document, arrow = False):
        super().__init__(document, "Arrow" if arrow else "Line")

        self.arrow = arrow

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
            cr.set_line_width(self.width)
            cr.set_dash([])
            cr.move_to(self.anchor1.x, self.anchor1.y)
            cr.line_to(self.anchor2.x, self.anchor2.y)

            if self.arrow:
                arrow_length = 0
                arrow_angle = math.atan2(self.anchor2.y - self.anchor1.y, self.anchor2.x - self.anchor1.x)
                arrowhead_angle = math.pi/6
                arrowhead_length = 7 * self.width

                cr.rel_line_to(arrow_length * math.cos(arrow_angle), arrow_length * math.sin(arrow_angle))
                cr.rel_move_to(-arrowhead_length * math.cos(arrow_angle - arrowhead_angle), -arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
                cr.rel_line_to(arrowhead_length * math.cos(arrow_angle - arrowhead_angle), arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
                cr.rel_line_to(-arrowhead_length * math.cos(arrow_angle + arrowhead_angle), -arrowhead_length * math.sin(arrow_angle + arrowhead_angle))

            cr.stroke()

class TextAnnotationLayer(PointLayer):

    text = GObject.Property(type=str, default="Text", nick="Text", blurb="type=multiline;order=2")
    text_markup = GObject.Property(type=bool, default=True, nick="Text as Markup", blurb="order=3")
    size = GObject.Property(type=int, default=50, nick="Size", minimum=1, maximum=1000, blurb="step1=10;step2=100;order=5")
    font = GObject.Property(type=Font, default=Font("Noto Sans Bold"), nick="Font", blurb="size=False;order=4")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color", blurb="order=6")
    centered = GObject.Property(type=bool, default=True, nick="Center", blurb="order=7")
    line_spacing = GObject.Property(type=float, default=1.0, nick="Line Spacing", minimum=0.01, maximum=2.0, blurb="step1=0.01;step2=0.1;order=8")

    def __init__(self, document):
        super().__init__(document, "Text")

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            # map GTK font description to Pango
            desc = Pango.font_description_from_string(self.font.desc)
            desc.set_size(self.size * Pango.SCALE)

            # layout options
            layout = PangoCairo.create_layout(cr)
            layout.set_font_description(desc)
            layout.set_alignment(Pango.Alignment.CENTER if self.centered else Pango.Alignment.LEFT)
            layout.set_line_spacing(self.line_spacing)
            if self.text_markup:
                layout.set_markup(self.text, -1)
            else:
                layout.set_text(self.text, -1)

            # font options
            fo = cairo.FontOptions()
            fo.set_antialias(cairo.ANTIALIAS_DEFAULT) # ANTIALIAS_SUBPIXEL
            PangoCairo.context_set_font_options(layout.get_context(), fo)

            # center or not
            width, height = layout.get_pixel_size()
            if self.centered:
                cr.translate(self.anchor.x - width / 2, self.anchor.y - height / 2)
            else:
                cr.translate(self.anchor.x, self.anchor.y)

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

    size = GObject.Property(type=int, default=150, nick="Size", minimum=1, maximum=1000, blurb="order=3")
    emoji = GObject.Property(type=Selector, default=Selector.SMALL_EMOJI_SELECTOR, nick="Emoji", blurb="order=2")

    def __init__(self, document):
        super().__init__(document, "Emoji")

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

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
            cr.translate(self.anchor.x - width / 2, self.anchor.y - height / 2)

            # render on surface to apply alpha
            cr.set_source_rgba(1, 1, 1, 1)
            PangoCairo.show_layout(cr, layout)

class LightingLayer(RectLayer):

    brightness = GObject.Property(type=float, default=1.5, nick="Brightness", minimum=0.0, maximum=10.0, blurb="order=2")
    contrast = GObject.Property(type=float, default=1.0, nick="Contrast", minimum=0.0, maximum=10.0, blurb="order=3")
    sharpness = GObject.Property(type=float, default=1.0, nick="Sharpness", minimum=0.0, maximum=10.0, blurb="order=4")
    color = GObject.Property(type=float, default=1.0, nick="Color", minimum=0.0, maximum=10.0, blurb="order=5")

    def __init__(self, document):
        super().__init__(document, "Lighting")

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:
                self._image = self.document.get_previous_render().crop((x1, y1, x2, y2))

                image = ImageEnhance.Brightness(self._image).enhance(self.brightness)
                image = ImageEnhance.Contrast(image).enhance(self.contrast)
                image = ImageEnhance.Sharpness(image).enhance(self.sharpness)
                image = ImageEnhance.Color(image).enhance(self.color)

                self._image_surface = cario_image_from_pil(image)

                # draw it
                cr.set_source_surface(self._image_surface, x1, y1)
                cr.paint()

class BlurLayer(RectLayer):

    box = GObject.Property(type=float, default=0.0, nick="Box Blur", minimum=0.0, maximum=10.0, blurb="order=2")
    gaussian = GObject.Property(type=float, default=10.0, nick="Gaussian Blur", minimum=0.0, maximum=10.0, blurb="order=3")

    def __init__(self, document):
        super().__init__(document, "Blur")

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():
            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:
                self._image = self.document.get_previous_render().crop((x1, y1, x2, y2))

                image = self._image.filter(ImageFilter.BoxBlur(self.box))
                image = image.filter(ImageFilter.GaussianBlur(self.gaussian))

                self._image_surface = cario_image_from_pil(image)

                # draw it
                cr.set_source_surface(self._image_surface, x1, y1)
                cr.paint()

class ZoomAnnotationLayer(RectLayer):

    zoom = GObject.Property(type=float, default=1.5, nick="Zoom", minimum=0.1, maximum=10.0, blurb="order=2")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Frame Color", blurb="order=4")
    frame = GObject.Property(type=bool, default=True, nick="Frame", blurb="order=3")
    frame_width = GObject.Property(type=int, default=3, nick="Frame Width", minimum=1, maximum=10, blurb="order=5")
    shadow = GObject.Property(type=bool, default=True, nick="Shadow", blurb="order=6")
    shadow_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(0, 0, 0, 1), nick="Shadow Color", blurb="order=7")
    shadow_extend = GObject.Property(type=int, default=15, nick="Shadow Extend", minimum=0, maximum=100, blurb="order=8")

    def __init__(self, document):
        super().__init__(document, "Zoom")

        # add zoom frame anchor
        self.anchor3 = self._add_anchor()

    def valid(self):
        return super().valid() and self.anchor3 != None and self.anchor3.valid()

    def on_anchors(self, x, y):
        return super().on_anchors(x, y) or self.anchor3.within(x, y, 10)

    def mouse_move(self, w, cr, mouse_x, mouse_y):
        super().mouse_move(w, cr, mouse_x, mouse_y)

        if self.dirty and super().valid():
            self.anchor3.set(self.anchor2.x + 0.5 * (self.anchor2.x - self.anchor1.x), self.anchor2.y + 0.5 * (self.anchor2.y - self.anchor1.y))
            self.anchor3 = self.anchor3

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            # normalize
            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:

                # crop image
                image = self.document.get_previous_render().crop((x1, y1, x2, y2))
                self._image_surface = cario_image_from_pil(image)

                # computation
                source_x = x1
                source_y = y1
                source_width = x2 - x1
                source_height = y2 - y1
                target_width = (x2 - x1) * self.zoom
                target_height = (y2 - y1) * self.zoom
                target_frame_x = self.anchor3.x - target_width / 2
                target_frame_y = self.anchor3.y - target_height / 2

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
                cr.translate(target_frame_x, target_frame_y)
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

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Stroke Width", minimum=0, maximum=50, blurb="order=3")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color", blurb="order=2")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color", blurb="order=6")
    dashed = GObject.Property(type=bool, default=False, nick="Dashed", blurb="order=4")
    closed = GObject.Property(type=bool, default=False, nick="Closed", blurb="order=5")

    def __init__(self, document):
        super().__init__(document, "Path")

        self.points = []
        self.anchor = self._add_anchor()
        self._moving = False

    def valid(self):
        return self.anchor != None and self.anchor.valid()

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):
        handled = super().mouse_down(w, cr, mouse_x, mouse_y, mouse_button)

        if not handled and mouse_button == 1 and not self.anchor.within(mouse_x, mouse_y, 10):
            self._moving = True
            self.dirty = True
            self.anchor.set(mouse_x, mouse_y)
            self.points = []
            self.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))
            handled = True

        return handled

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self._moving:
            self._moving = False
            self.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))
            self.dirty = False

    def mouse_move(self, w, cr, mouse_x, mouse_y):
        super().mouse_move(w, cr, mouse_x, mouse_y)

        if self._moving and self.dirty:
            self.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid() and len(self.points) >= 1:
            cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)

            cr.new_path()
            cr.move_to(self.anchor.x, self.anchor.y)
            for x, y in self.points:
                cr.line_to(self.anchor.x + x, self.anchor.y + y)

            if self.closed:
                cr.close_path()

            cr.fill_preserve()

            cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
            if self.dashed:
                cr.set_dash([self.width, self.width])
            cr.set_line_width(self.width)

            cr.stroke()

class ImageAnnotationLayer(RectLayer):

    path = GObject.Property(type=str, nick="Path", blurb="type=file;order=2")
    keep_aspect = GObject.Property(type=bool, default=True, nick="Keep Aspect", blurb="order=3")
    alpha = GObject.Property(type=float, default=1.0, nick="Alpha", minimum=0.0, maximum=1.0, blurb="order=4")

    def __init__(self, document, path=None):
        super().__init__(document, "Image")

        self.path = path
        self._image_surface = None

        if self.path != None:
            self._reload_image()

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

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        # ask for the image if needed
        if mouse_button == 1:
            self.ask_for_image_if_needed()

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            if self._image_surface == None:
                cr.set_source_rgba(1, 1, 1, 0.75)
                cr.set_line_width(DEFAULT_WIDTH)
                cr.set_dash([10, 10])
                cr.rectangle(self.anchor1.x, self.anchor1.y, self.anchor2.x - self.anchor1.x, self.anchor2.y - self.anchor1.y)
                cr.stroke()
            else:

                source_w = self._image_surface.get_width()
                source_h = self._image_surface.get_height()
                target_w = self.anchor2.x - self.anchor1.x
                target_h = self.anchor2.y - self.anchor1.y
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
                    cr.translate(self.anchor1.x, self.anchor1.y)
                    cr.scale(scale_x, scale_y)
                    cr.set_source_surface(self._image_surface, 0, 0)
                    cr.paint_with_alpha(self.alpha)
                    cr.restore()

class CloneAnnotationLayer(RectLayer):

    live = GObject.Property(type=bool, default=False, nick="Live", blurb="order=2")
    zoom = GObject.Property(type=float, default=1, nick="Zoom", minimum=0.1, maximum=10.0, blurb="order=3")
    frame = GObject.Property(type=bool, default=True, nick="Frame", blurb="order=4")
    frame_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Frame Color", blurb="order=5")
    frame_width = GObject.Property(type=int, default=3, nick="Frame Width", minimum=1, maximum=10, blurb="order=6")
    frame_dashed = GObject.Property(type=bool, default=False, nick="Dashed", blurb="order=7")
    shadow = GObject.Property(type=bool, default=True, nick="Shadow", blurb="order=8")
    shadow_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(0, 0, 0, 1), nick="Shadow Color", blurb="order=9")
    shadow_extend = GObject.Property(type=int, default=15, nick="Shadow Extend", minimum=0, maximum=100, blurb="order=10")

    def __init__(self, document, live=None):
        super().__init__(document, "Clone")

        if live != None:
            self.live = live

        self._snap_x1 = 0
        self._snap_y1 = 0
        self._snap_x2 = 0
        self._snap_y2 = 0

        self._image_surface = None

    def clear(self):
        self._image_surface = None

    def clone(self):

        x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

        if ok:
            self._snap_x1 = x1
            self._snap_y1 = y1
            self._snap_x2 = x2
            self._snap_y2 = y2

            image = self.document.get_previous_render().crop((x1, y1, x2, y2))
            self._image_surface = cario_image_from_pil(image)

    def mouse_down(self, w, cr, mouse_x, mouse_y, mouse_button):
        if not self.between_anchors(mouse_x, mouse_y) and Layer.KEY_CONTROL:
            self.clear()

        return super().mouse_down(w, cr, mouse_x, mouse_y, mouse_button)

    def mouse_up(self, w, cr, mouse_x, mouse_y, mouse_button):
        dirty = self.dirty

        super().mouse_up(w, cr, mouse_x, mouse_y, mouse_button)

        # update the snap
        if mouse_button == 1 and dirty:
            self.dirty = False

            # clone
            self.clone()

            # link anchors and hide second anchor
            self.anchor2.visible = False
            self.anchor1.link(self.anchor2)

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self.valid():

            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:

                # copy
                image_surface = None
                if self.live:
                    # dynamic clone
                    image = self.document.get_previous_render().crop((self._snap_x1, self._snap_y1, self._snap_x2, self._snap_y2))
                    image_surface = cario_image_from_pil(image)
                elif self._image_surface != None:
                    # static clone
                    image_surface = self._image_surface
                else:
                    # not live, no static image: it means we are building up the frame
                    image = self.document.get_previous_render().crop((x1, y1, x2, y2))
                    image_surface = cario_image_from_pil(image)

                if image_surface != None:

                    # computation
                    target_frame_x = x1
                    target_frame_y = y1
                    target_width = image_surface.get_width() * self.zoom
                    target_height = image_surface.get_height() * self.zoom

                    # image
                    cr.save()
                    cr.translate(x1, y1)
                    cr.scale(self.zoom, self.zoom)
                    cr.set_source_surface(image_surface, 0, 0)
                    cr.paint()
                    cr.restore()

                    # shadow
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

                    # frame
                    if self.frame:
                        cr.set_source_rgba(self.frame_color.red, self.frame_color.green, self.frame_color.blue, self.frame_color.alpha)
                        cr.set_line_width(self.frame_width)
                        cr.set_dash([] if not self.frame_dashed else [self.frame_width, self.frame_width])
                        cr.rectangle(x1, y1, target_width, target_height)
                        cr.stroke()

