from .layers import *
import copy

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

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1 and self.within(mouse_x, mouse_y, 10):
            self._grabbed = True
            self.set(mouse_x, mouse_y)

            # linked anchors
            for anchor in self.linked_anchors:
                self.linked_anchors[anchor] = (anchor.x - self.x, anchor.y - self.y)

            return True

        return False


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
            return distance <= (Anchor.ANCHOR_RADIUS + precision)
        return False

    def draw(self, doc, w, cr):
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

class Tool:

    # keys modifiers
    KEY_CONTROL = False
    KEY_SHIFT = False
    KEY_ALT = False

    def __init__(self, document, layer, reticule=False, draw_anchors=True):
        assert layer != None, "Layer can't be undefined!"

        self.document = document
        self.reticule = reticule
        self.draw_anchors = draw_anchors

        # layer reference
        self.layer = layer

        # layer tool reference
        self.layer.tool = self

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

    def hit_test(self, x, y):
        hit = False
        for anchor in self.anchors:
            if anchor.hit_test(x, y):
                hit = True
                break

        return hit

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):

        # anchors
        handled = False
        for anchor in self.anchors:
            if anchor.mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button) and not handled:
                handled = True

        return handled

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
        handled = super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if not handled and mouse_button == 1 and (self.layer.dirty or Tool.KEY_CONTROL):
            self._moving = True
            self.anchor.set(mouse_x, mouse_y)
            handled = True

        return handled

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

    RECT_TYPE_NONE = 0
    RECT_TYPE_CLASSIC = 1
    RECT_TYPE_CONTRAST = 1

    def __init__(self, document, layer=None, rect=RECT_TYPE_NONE, persistent_rect=False, draw_anchors=True):
        super().__init__(document, layer, reticule=True, draw_anchors=draw_anchors)

        # anchors
        if layer is None:
            self.anchor1 = None
            self.anchor2 = None
        elif layer.dirty:
            self.anchor1 = super()._add_anchor()
            self.anchor2 = super()._add_anchor()
        else:
            self.anchor1 = super()._add_anchor(layer.anchor1.x, layer.anchor1.y)
            self.anchor2 = super()._add_anchor(layer.anchor2.x, layer.anchor2.y)

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

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        handled = super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # first anchor position
        if not handled and mouse_button == 1:
            if self.layer.dirty:
                self._init = True
                self.anchor1.set(mouse_x, mouse_y)
                handled = True
            elif self.between_anchors(mouse_x, mouse_y):
                self._moving = (mouse_x, mouse_y)
                self._moving_anchor1 = copy.deepcopy(self.anchor1)
                self._moving_anchor2 = copy.deepcopy(self.anchor2)
                handled = True
            elif not self.on_anchors(mouse_x, mouse_y) and Tool.KEY_CONTROL:
                self._init = True
                self.layer.dirty = True
                self.anchor1.set(mouse_x, mouse_y)
                handled = True

        return handled

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            if self._init:
                self.layer.dirty = False
                self._init = False
                self.anchor2.set(mouse_x, mouse_y)
            elif self._moving != None:
                self._moving = None

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

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

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        self._sync_layer()

        # rect
        if self.rect != RectTool.RECT_TYPE_NONE and (self.persistent_rect or not self.layer.dirty) and self.valid():
            x1, y1, x2, y2, ok = normalize_rect(self.anchor1.x, self.anchor1.y, self.anchor2.x, self.anchor2.y)

            if ok:
                width = doc.imageSurface.get_width()
                height = doc.imageSurface.get_height()

                if self.rect == RectTool.RECT_TYPE_CLASSIC:
                    scale = 1 / (doc.scale / 100)

                    cr.set_source_rgba(Anchor.ANCHOR_COLOR[0], Anchor.ANCHOR_COLOR[1], Anchor.ANCHOR_COLOR[2], Anchor.ANCHOR_COLOR[3])
                    cr.set_operator(Anchor.ANCHOR_OPERATOR);
                    cr.set_line_width(Anchor.ANCHOR_WIDTH * scale)

                    cr.set_dash([Anchor.ANCHOR_WIDTH * scale * 5, Anchor.ANCHOR_WIDTH * scale * 5])
                    cr.rectangle(x1, y1, x2 - x1, y2 - y1)
                    cr.stroke()
                elif self.rect == RectTool.RECT_TYPE_CONTRAST:
                    cr.set_source_rgba(0, 0, 0, 0.5)
                    cr.set_line_width(0)
                    cr.set_dash([])
                    cr.rectangle(0, 0, width, y1)
                    cr.rectangle(0, 0, x1, height)
                    cr.rectangle(x2, 0, width - x2, height)
                    cr.rectangle(0, y2, width, height - y2)
                    cr.fill()

        super().draw(doc, w, cr, mouse_x, mouse_y)

    def _sync_layer(self):
        # propagate to layer (which should inherit RectLayer)
        if self.layer != None:
            self.layer.anchor1 = self.anchor1
            self.layer.anchor2 = self.anchor2

class CropTool(RectTool):

    # TODO use layer to allow modifying cropping

    def __init__(self, document):
        super().__init__(document, None, rect=RectTool.RECT_TYPE_CONTRAST, draw_anchors=False)

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
            layer = RectangleAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)


class CircleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = CircleAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

        # link both anchors
        self.anchor1.link(self.anchor2)

    def between_anchors(self, x, y):
        if self.valid() and not self.on_anchors(x, y):
            radius = math.sqrt((self.anchor2.x - self.anchor1.x)**2 + (self.anchor2.y - self.anchor1.y)**2)
            distance = math.sqrt((self.anchor1.x - x)**2 + (self.anchor1.y - y)**2)
            return distance <= radius
        return False

class EllipseAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = EllipseAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer, rect=RectTool.RECT_TYPE_CLASSIC, persistent_rect=True)

class LineAnnotationTool(RectTool):

    def __init__(self, document, layer=None, arrow=False):
        if layer == None:
            layer = LineAnnotationLayer(document, self, arrow=arrow)
            document.add_layer(layer)

        super().__init__(document, layer)

class TextAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = TextAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

class EmojiAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = EmojiAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

class LightingTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = LightingLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

class BlurTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = BlurLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

class ZoomAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = ZoomAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

        # add zoom frame anchor
        self.anchor3 = self._add_anchor()

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self.layer.dirty and self.valid():
            self.anchor3.set(self.anchor2.x + 0.5 * (self.anchor2.x - self.anchor1.x), self.anchor2.y + 0.5 * (self.anchor2.y - self.anchor1.y))
            self.layer.anchor3 = self.anchor3

    def on_anchors(self, x, y):
        return super().on_anchors(x, y) or self.anchor3.within(x, y, 10)
        
class PathAnnotationTool(Tool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = PathAnnotationLayer(document, self)
            document.add_layer(layer)

        super().__init__(document, layer)

        self.anchor = self._add_anchor() if layer.dirty else layer.anchor

        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        handled = super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if not handled and mouse_button == 1 and not self.anchor.within(mouse_x, mouse_y, 10):
            self._moving = True
            self.layer.dirty = True
            self.anchor.set(mouse_x, mouse_y)
            self.layer.points = []
            self.layer.points.append((mouse_x - self.anchor.x, mouse_y - self.anchor.y))
            handled = True

        return handled

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
            layer = ImageAnnotationLayer(document, self)
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

        super().__init__(document, layer, self)

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        if not self.between_anchors(mouse_x, mouse_y):
            self.layer.clear()

        return super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        dirty = self.layer.dirty

        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # update the snap
        if mouse_button == 1 and dirty:
            self.layer.dirty = False

            # clone
            self.layer.clone()

            # link anchors and hide second anchor
            self.anchor2.visible = False
            self.anchor1.link(self.anchor2)

