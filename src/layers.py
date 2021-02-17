import cairo
import gi
from gi.repository import Gtk, Gio, GObject

class Layer(GObject.GObject):

    name = GObject.Property(type=str)

    def __init__(self, name):
        GObject.GObject.__init__(self)
        self.name = name

    def draw(self, w, cr):
        pass

class RectangleLayer(Layer):

    def __init__(self, x1 = 0, y1 = 0, x2 = 0, y2 = 0):
        super().__init__("Rectangle")
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def draw(self, w, cr):
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(1)
        cr.set_dash([])
        cr.rectangle(self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)
        cr.stroke()
