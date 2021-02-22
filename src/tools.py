from .layers import *

class Tool:

    # keys modifiers
    KEY_CONTROL = False
    KEY_SHIFT = False
    KEY_ALT = False

    def __init__(self, document, layer=None, reticule=False, callback=None):
        self.document = document
        self.apply_callback = callback
        self.reticule = reticule

        # layer reference
        self.layer = layer

        # drawing
        self.drawing = False

        # moving
        self.moving = False
        self._start_move_offset_x = 0
        self._start_move_offset_y = 0
        self.offset_x = 0
        self.offset_y = 0
        self.cumulated_offset_x = 0 if layer is None else layer.offset_x
        self.cumulated_offset_y = 0 if layer is None else layer.offset_y

    # static key handler to process custom keys
    def on_key(widget, event):
        Tool.KEY_CONTROL = (event.keyval == Gdk.KEY_Control_L or event.keyval == Gdk.KEY_Control_R) and event.type == Gdk.EventType.KEY_PRESS
        Tool.KEY_SHIFT = (event.keyval == Gdk.KEY_Shift_L or event.keyval == Gdk.KEY_Shift_R) and event.type == Gdk.EventType.KEY_PRESS
        Tool.KEY_ALT = (event.keyval == Gdk.KEY_Alt_L or event.keyval == Gdk.KEY_Alt_R) and event.type == Gdk.EventType.KEY_PRESS

    def apply(self):
        if self.apply_callback != None:
            self.apply_callback()

    def cancel(self):
        self.drawing = False
        self.moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):

        if not self.drawing and mouse_button == 1:
            self.cumulated_offset_x = 0
            self.cumulated_offset_y = 0
            self._update_offset(0, 0)
            self.drawing = True

        if not self.moving and mouse_button == 3:
            self.cumulated_offset_x += self.offset_x
            self.cumulated_offset_y += self.offset_y
            self.offset_x = 0
            self.offset_y = 0

            self._start_move_offset_x = mouse_x
            self._start_move_offset_y = mouse_y

            self.moving = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        if mouse_button == 1:
            self.drawing = False

        if mouse_button == 3:
            self.moving = False

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        if self.moving:
            self._update_offset(mouse_x - self._start_move_offset_x, mouse_y - self._start_move_offset_y)

    def _update_offset(self, offset_x, offset_y):
        self.offset_x = offset_x
        self.offset_y = offset_y

    def draw(self, doc, w, cr, mouse_x, mouse_y):

        # offset
        if self.layer != None:
            self.layer.offset_x = self.cumulated_offset_x + self.offset_x
            self.layer.offset_y = self.cumulated_offset_y + self.offset_y

        # reticule
        if self.reticule:
            cr.set_source_rgb(1, 1, 1)
            cr.set_dash([10, 10])
            cr.set_line_width(1)

            cr.move_to(mouse_x, 0)
            cr.line_to(mouse_x, doc.imageSurface.get_height())

            cr.move_to(0, mouse_y)
            cr.line_to(doc.imageSurface.get_width(), mouse_y)

            cr.stroke()

class PointTool(Tool):

    def __init__(self, document, layer):
        super().__init__(document, layer, reticule = True)
        self.x = 0
        self.y = 0

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.x = mouse_x
            self.y = mouse_y

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.x = mouse_x
            self.y = mouse_y
            self.apply()

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self.drawing:
            self.x = mouse_x
            self.y = mouse_y

            # propagate to layer (which should inherit PointLayer)
            if self.layer != None:
                self.layer.x = self.x
                self.layer.y = self.y

class RectTool(Tool):

    def __init__(self, document, layer=None, normalize=True):
        super().__init__(document, layer, reticule = True)

        self.normalize = normalize

        self.x1 = 0 if layer == None else layer.x1
        self.y1 = 0 if layer == None else layer.y1
        self.x2 = 0 if layer == None else layer.x2
        self.y2 = 0 if layer == None else layer.y2

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.x1 = mouse_x
            self.y1 = mouse_y

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.x2 = mouse_x
            self.y2 = mouse_y
            self._normalize()
            self.apply()

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self.drawing:
            self.x2 = mouse_x
            self.y2 = mouse_y
            self._normalize()

            # propagate to layer (which should inherit RectLayer)
            if self.layer != None:
                self.layer.x1 = self.x1
                self.layer.y1 = self.y1
                self.layer.x2 = self.x2
                self.layer.y2 = self.y2

    def _normalize(self):
        if self.normalize:
            self.x1 = min(self.x1, self.x2)
            self.y1 = min(self.y1, self.y2)
            self.x2 = max(self.x1, self.x2)
            self.y2 = max(self.y1, self.y2)


class CropTool(RectTool):

    def __init__(self, document):
        super().__init__(document)

    def apply(self):
        super().apply()

        self.document.crop(self.x1, self.y1, self.x2, self.y2)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self.drawing:
            width = doc.imageSurface.get_width()
            height = doc.imageSurface.get_height()

            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, width, self.y1)
            cr.rectangle(0, 0, self.x1, height)
            cr.rectangle(mouse_x, 0, mouse_x, height)
            cr.rectangle(0, mouse_y, width, mouse_y)
            cr.fill()

class RectangleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = RectangleAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer, normalize=False)

class EllipseAnnotationTool(RectTool):

    def __init__(self, document, layer=None, circle=False):
        if layer == None:
            layer = EllipseAnnotationLayer(document, circle=circle)
            document.add_layer(layer)

        super().__init__(document, layer, normalize=False)

class LineAnnotationTool(RectTool):

    def __init__(self, document, layer=None, arrow=False):
        if layer == None:
            layer = LineAnnotationLayer(document, arrow=arrow)
            document.add_layer(layer)

        super().__init__(document, layer, normalize=False)

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

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self.drawing or self.moving:
            self.layer.updating = True

class BlurTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = BlurLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self.drawing or self.moving:
            self.layer.updating = True

class ZoomAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = ZoomAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer, normalize=True)

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.layer.clear()

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        if self.moving and Tool.KEY_CONTROL:
            self.layer.frame_position_forced = True
            self.layer.frame_x = mouse_x
            self.layer.frame_y = mouse_y
        else:
           super().mouse_move(doc, w, cr, mouse_x, mouse_y)

           if self.moving:
               self.layer.update()

    def apply(self):
        super().apply()

        self.layer.update()

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self.drawing:
            width = doc.imageSurface.get_width()
            height = doc.imageSurface.get_height()

            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, width, self.y1)
            cr.rectangle(0, 0, self.x1, height)
            cr.rectangle(mouse_x, 0, mouse_x, height)
            cr.rectangle(0, mouse_y, width, mouse_y)
            cr.fill()
        
class PathAnnotationTool(Tool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = PathAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer, reticule = True)

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.layer.points = []
            self.layer.points.append((mouse_x, mouse_y))

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            self.layer.points.append((mouse_x, mouse_y))

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self.drawing:
            self.layer.points.append((mouse_x, mouse_y))

class ImageAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        if layer == None:
            layer = ImageAnnotationLayer(document)
            document.add_layer(layer)

        super().__init__(document, layer, normalize=False)

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # ask for the image if needed
        self.layer.ask_for_image_if_needed()
