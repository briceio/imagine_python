import cairo
import gi
from gi.repository import Gtk, Gio, GObject

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

    width = GObject.Property(type=int, nick="Width")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Rectangle")
        self.width = 1
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
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.stroke()


class ArrowAnnotationLayer(Layer):

    width = GObject.Property(type=int, nick="Width")

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Arrow")
        self.width = 1
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def get_tool(self):
        return "ArrowAnnotationTool"

    def crop(self, x1, y1, x2, y2):
        self.x1 -= x1
        self.y1 -= y1
        self.x2 -= x1
        self.y2 -= y1

    def draw(self, w, cr):
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(self.width)
        cr.set_dash([])
        cr.move_to(self.x1, self.y1)
        cr.line_to(self.x2, self.y2)
        cr.stroke()
