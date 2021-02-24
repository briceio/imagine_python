from .layers import *

class Anchor:

    def __init__(self, x=None, y=None, radius=10):
        self.set(x, y)

        # visible flag
        self.visible = True

        # linked anchors
        self.linked_anchors = {}

        self.radius = radius

        self._grabbed = False

    def set(self, x, y):
        self.x = x
        self.y = y

    def valid(self):
        return self.x != None and self.y != None

    def link(self, anchor):
        self.linked_anchors[anchor] = None

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1 and self.within(mouse_x, mouse_y, 10):
            self._grabbed = True
            self.set(mouse_x, mouse_y)

            # linked anchors
            for anchor in self.linked_anchors:
                self.linked_anchors[anchor] = (anchor.x - self.x, anchor.y - self.y)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1 and self._grabbed:
            self._grabbed = False
            self.set(mouse_x, mouse_y)

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
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
            return distance <= (self.radius + precision)
        return False

    def draw(self, doc, w, cr):
        if self.visible and self.valid():
            cr.save()

            scale = 1 / (doc.scale / 100)
            radius = self.radius * scale

            cr.set_source_rgba(0, 0, 0, 0.7)
            cr.arc(self.x, self.y, radius, 0, math.pi * 2)
            cr.fill_preserve()

            cr.set_source_rgba(1, 1, 1, 0.7)
            cr.set_line_width(3)
            cr.set_dash([])
            cr.stroke()
            cr.restore()

class Tool:

    # keys modifiers
    KEY_CONTROL = False
    KEY_SHIFT = False
    KEY_ALT = False

    def __init__(self, document, layer=None, reticule=False, draw_anchors=True):
        self.document = document
        self.reticule = reticule
        self.draw_anchors = draw_anchors

        # layer reference
        self.layer = layer

        # anchors
        self.anchors = []

    # static key handler to process custom keys
    def on_key(widget, event):
        Tool.KEY_CONTROL = (event.keyval == Gdk.KEY_Control_L or event.keyval == Gdk.KEY_Control_R) and event.type == Gdk.EventType.KEY_PRESS
        Tool.KEY_SHIFT = (event.keyval == Gdk.KEY_Shift_L or event.keyval == Gdk.KEY_Shift_R) and event.type == Gdk.EventType.KEY_PRESS
        Tool.KEY_ALT = (event.keyval == Gdk.KEY_Alt_L or event.keyval == Gdk.KEY_Alt_R) and event.type == Gdk.EventType.KEY_PRESS

    def _add_anchor(self, x=None, y=None):
        anchor = Anchor(x, y)
        self.anchors.append(anchor)
        return anchor

    def _remove_anchor(self, anchor):
        self.anchors.remove(anchor)

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):

        # anchors
        for anchor in self.anchors:
            anchor.mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):

        # anchors
        for anchor in self.anchors:
            anchor.mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):

        # anchors
        for anchor in self.anchors:
            anchor.mouse_move(doc, w, cr, mouse_x, mouse_y)

    def valid(self):
        return True

    def draw(self, doc, w, cr, mouse_x, mouse_y):

        # reticule
        if self.reticule:
            cr.set_source_rgba(1, 1, 1, 0.7)
            cr.set_dash([10, 10])
            cr.set_line_width(1)

            cr.move_to(mouse_x, 0)
            cr.line_to(mouse_x, doc.imageSurface.get_height())

            cr.move_to(0, mouse_y)
            cr.line_to(doc.imageSurface.get_width(), mouse_y)

            cr.stroke()

        # anchors
        if self.draw_anchors:
            for anchor in self.anchors:
                anchor.draw(doc, w, cr)

class PointTool(Tool):

    def __init__(self, document, layer, draw_anchors=True):
        super().__init__(document, layer, reticule=True, draw_anchors=draw_anchors)

        # anchor
        if layer.dirty:
            self.anchor = super()._add_anchor()
        else:
            self.anchor = super()._add_anchor(layer.anchor.x, layer.anchor.y)

        # initial position
        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if mouse_button == 1 and self.layer.dirty:
            self._moving = True
            self.anchor.set(mouse_x, mouse_y)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self._moving:
            self.layer.dirty = False
            self._moving = False
            self.anchor.set(mouse_x, mouse_y)

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._moving:
            self.anchor.set(mouse_x, mouse_y)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        self._sync_layer()

    def valid(self):
        return self.anchor1 != None and self.anchor1.valid()

    def _sync_layer(self):
        # propagate to layer (which should inherit PointLayer)
        if self.layer != None:
            self.layer.anchor = self.anchor

class RectTool(Tool):

    def __init__(self, document, layer=None, draw_rect=False, draw_anchors=True):
        super().__init__(document, layer, reticule=True, draw_anchors=draw_anchors)

        # anchors
        if layer.dirty:
            self.anchor1 = super()._add_anchor()
            self.anchor2 = super()._add_anchor()
        else:
            self.anchor1 = super()._add_anchor(layer.anchor1.x, layer.anchor1.y)
            self.anchor2 = super()._add_anchor(layer.anchor2.x, layer.anchor2.y)

        self.draw_rect = draw_rect

        # initial position
        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if mouse_button == 1 and self.layer.dirty:
            self._moving = True
            self.anchor1.set(mouse_x, mouse_y)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self._moving:
            self.layer.dirty = False
            self._moving = False
            self.anchor2.set(mouse_x, mouse_y)

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._moving:
            self.anchor2.set(mouse_x, mouse_y)

    def valid(self):
        return self.anchor1 != None and self.anchor2 != None and self.anchor1.valid() and self.anchor2.valid()

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        self._sync_layer()

        if self.draw_rect and not self.layer.dirty and self.valid():
            x1, y1, x2, y2 = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if x2 - x1 <= 0 or y2 - y1 <= 0:
                return

            width = doc.imageSurface.get_width()
            height = doc.imageSurface.get_height()

            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, width, y1)
            cr.rectangle(0, 0, x1, height)
            cr.rectangle(x2, 0, width - x2, height)
            cr.rectangle(0, y2, width, height - y2)
            cr.fill()

    def _sync_layer(self):
        # propagate to layer (which should inherit RectLayer)
        if self.layer != None:
            self.layer.anchor1 = self.anchor1
            self.layer.anchor2 = self.anchor2

class CropTool(RectTool):

    # TODO use layer to allow modifying cropping

    def __init__(self, document):
        super().__init__(document, draw_rect=True, draw_anchors=False)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self.valid():
            x1, y1, x2, y2 = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if x2 - x1 <= 0 or y2 - y1 <= 0:
                return

            self.document.crop(x1, y1, x2, y2)

class RectangleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = RectangleAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)


class CircleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = CircleAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

        # link both anchors
        self.anchor1.link(self.anchor2)

class EllipseAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = EllipseAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

class LineAnnotationTool(RectTool):

    def __init__(self, document, layer=None, arrow=False):
        if layer == None:
            layer = LineAnnotationLayer(document, arrow=arrow)
            document.add_layer(layer)

        super().__init__(document, layer)

class TextAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = TextAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

class EmojiAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = EmojiAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

class LightingTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = LightingLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

class BlurTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = BlurLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

class ZoomAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = ZoomAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

        # add zoom frame anchor
        self.anchor3 = self._add_anchor()

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._init and self.valid():
            self.anchor3.set(self.anchor2.x + 0.5 * (self.anchor2.x - self.anchor1.x), self.anchor2.y + 0.5 * (self.anchor2.y - self.anchor1.y))
            self.layer.anchor3 = self.anchor3
        
class PathAnnotationTool(Tool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = PathAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

        self.anchor = self._add_anchor() if layer.dirty else layer.anchor

        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and not self.anchor.within(mouse_x, mouse_y, 10):
            self._moving = True
            self.layer.dirty = True
            self.anchor.set(mouse_x, mouse_y)
            self.layer.points = []
            self.layer.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1 and self._moving:
            self._moving = False
            self.layer.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))
            self.layer.dirty = False

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._moving and self.layer.dirty:
            self.layer.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        self._sync_layer()

    def valid(self):
        return self.anchor != None and self.anchor.valid()

    def _sync_layer(self):
        # propagate to layer (which should inherit PointLayer)
        if self.layer != None:
            self.layer.anchor = self.anchor


class ImageAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = ImageAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # ask for the image if needed
        if mouse_button == 1:
            self.layer.ask_for_image_if_needed()

class CloneAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = CloneAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

        self.cloned = False

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # update the snap
        if mouse_button == 1 and not self.cloned:
            self.cloned = True

            # clone
            self.layer.clone()

            # link anchors and hide second anchor
            self.anchor2.visible = False
            self.anchor1.link(self.anchor2)


