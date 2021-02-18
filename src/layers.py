import cairo
import gi
import math
from gi.repository import Gtk, Gdk, Gio, GObject

# common default tool widths
DEFAULT_WIDTH = 5

class Layer(GObject.GObject):

    name = GObject.Property(type=str, nick="Name")

    def __init__(self, name):
        GObject.GObject.__init__(self)
        self.name = name

    def get_tool(self):
        return None

    def draw(self, w, cr):
        pass

    def crop(self, x1, y1, x2, y2):
        pass

class RectangleAnnotationLayer(Layer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width")
    stroke_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Stroke Color")
    fill_color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 0), nick="Fill Color")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Rectangle")
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def get_tool(self):
        return "RectangleAnnotationTool"

    def crop(self, x1, y1, x2, y2):
        self.x1 -= x1
        self.y1 -= y1
        self.x2 -= x1
        self.y2 -= y1

    def draw(self, w, cr):
        cr.set_source_rgba(self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha)
        cr.set_line_width(0)
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.fill()

        cr.set_source_rgba(self.stroke_color.red, self.stroke_color.green, self.stroke_color.blue, self.stroke_color.alpha)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.stroke()


class LineAnnotationLayer(Layer):

    width = GObject.Property(type=int, default=DEFAULT_WIDTH, nick="Width")
    color = GObject.Property(type=Gdk.RGBA, default=Gdk.RGBA(1, 1, 1, 1), nick="Color")
    arrow = GObject.Property(type=bool, default=False, nick="Arrow")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0, arrow = False):
        super().__init__("Arrow" if arrow else "Line")
        self.arrow = arrow
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def get_tool(self):
        return "LineAnnotationTool"

    def crop(self, x1, y1, x2, y2):
        self.x1 -= x1
        self.y1 -= y1
        self.x2 -= x1
        self.y2 -= y1

    def draw(self, w, cr):
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
