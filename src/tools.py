from .layers import *

class Tool:

    def __init__(self, document, **args):
        self.document = document
        self.apply_callback = args["callback"] if "callback" in args else None
        self.reticule = bool(args["reticule"]) if "reticule" in args else False

    def apply(self):
        if self.apply_callback != None:
            self.apply_callback()

        pass

    def cancel(self):
        pass

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        pass

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        pass

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        pass

    def draw(self, doc, w, cr, mouse_x, mouse_y):

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

    def __init__(self, document):
        super().__init__(document, reticule = True)
        self._drawing = False
        self.x = 0
        self.y = 0

    def cancel(self):
        super().cancel()
        self._drawing = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)
        if not self._drawing:
            self.x = mouse_x
            self.y = mouse_y
            self._drawing = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if self._drawing:
            self.x = mouse_x
            self.y = mouse_y
            self.apply()

        self._drawing = False

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.x = mouse_x
            self.y = mouse_y

class RectTool(Tool):

    def __init__(self, document):
        super().__init__(document, reticule = True)
        self._drawing = False
        self._moving = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

        self._start_move_offset_x = 0
        self._start_move_offset_y = 0
        self._end_move_offset_x = 0
        self._end_move_offset_y = 0

    def cancel(self):
        super().cancel()
        self._drawing = False
        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if not self._drawing and mouse_button == 1:
            self.start_x = mouse_x
            self.start_y = mouse_y
            self._drawing = True

        if not self._moving and mouse_button == 3:
            self._start_move_offset_x = mouse_x - self.start_x
            self._start_move_offset_y = mouse_y - self.start_y
            self._end_move_offset_x = mouse_x - self.end_x
            self._end_move_offset_y = mouse_y - self.end_y
            self._moving = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            if self._drawing:
                self.end_x = mouse_x
                self.end_y = mouse_y
                self.apply()
            self._drawing = False

        if self._moving and mouse_button == 3:
            self._moving = False

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._moving:
            self.start_x = mouse_x - self._start_move_offset_x
            self.start_y = mouse_y - self._start_move_offset_y
            self.end_x = mouse_x - self._end_move_offset_x
            self.end_y = mouse_y - self._end_move_offset_y

    def normalize(self):
        return (min(self.start_x, self.end_x),
                min(self.start_y, self.end_y),
                max(self.start_x, self.end_x),
                max(self.start_y, self.end_y))

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.end_x = mouse_x
            self.end_y = mouse_y

    def width(self):
        return abs(int(self.end_x - self.start_x))

    def height(self):
        return abs(int(self.end_y - self.start_y))

class CropTool(RectTool):

    def __init__(self, document):
        super().__init__(document)

    def apply(self):
        super().apply()
        self.document.crop(self.start_x, self.start_y, self.end_x, self.end_y)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            width = doc.imageSurface.get_width()
            height = doc.imageSurface.get_height()

            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, width, self.start_y)
            cr.rectangle(0, 0, self.start_x, height)
            cr.rectangle(mouse_x, 0, mouse_x, height)
            cr.rectangle(0, mouse_y, width, mouse_y)
            cr.fill()

class RectangleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = RectangleAnnotationLayer(document)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            (x1, y1, x2, y2) = self.normalize()
            self.layer.x1 = x1
            self.layer.y1 = y1
            self.layer.x2 = x2
            self.layer.y2 = y2
            self.layer.draw(w, cr)

class EllipseAnnotationTool(RectTool):

    def __init__(self, document, layer=None, circle=False):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = EllipseAnnotationLayer(document,circle=circle)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            (x1, y1, x2, y2) = self.normalize()
            self.layer.x1 = x1
            self.layer.y1 = y1
            self.layer.x2 = x2
            self.layer.y2 = y2
            self.layer.draw(w, cr)

class LineAnnotationTool(RectTool):

    def __init__(self, document, layer=None, arrow=False):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = LineAnnotationLayer(document, arrow=arrow)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            self.layer.x1 = self.start_x
            self.layer.y1 = self.start_y
            self.layer.x2 = self.end_x
            self.layer.y2 = self.end_y
            self.layer.draw(w, cr)

class TextAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = TextAnnotationLayer(document)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.x = self.x
            self.layer.y = self.y
            self.layer.draw(w, cr)

class EmojiAnnotationTool(PointTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = EmojiAnnotationLayer(document)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.x = self.x
            self.layer.y = self.y
            self.layer.draw(w, cr)

class LightingTool(RectTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = LightingLayer(document)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            (x1, y1, x2, y2) = self.normalize()
            self.layer.x1 = x1
            self.layer.y1 = y1
            self.layer.x2 = x2
            self.layer.y2 = y2
            self.layer.updating = True
            self.layer.draw(w, cr)

class BlurTool(RectTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = BlurLayer(document)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            (x1, y1, x2, y2) = self.normalize()
            self.layer.x1 = x1
            self.layer.y1 = y1
            self.layer.x2 = x2
            self.layer.y2 = y2
            self.layer.updating = True
            self.layer.draw(w, cr)

class ZoomAnnotationTool(Tool):

    def __init__(self, document, layer=None):
        super().__init__(document, reticule = True)

        self.layer = layer
        if layer == None:
            self.layer = ZoomAnnotationLayer(document)
            self.document.add_layer(self.layer)

        self._drawing = False
        self._moving = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def cancel(self):
        super().cancel()
        self._drawing = False
        self._moving = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if not self._drawing and mouse_button == 1:
            self.start_x = mouse_x
            self.start_y = mouse_y
            self._drawing = True

        if not self._moving and mouse_button == 3:
            self._moving = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if mouse_button == 1:
            if self._drawing:
                self.end_x = mouse_x
                self.end_y = mouse_y
                self.apply()
            self._drawing = False

        if self._moving and mouse_button == 3:
            self._moving = False

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._moving:
            self.layer.frame_position_forced = True
            self.layer.frame_x = mouse_x
            self.layer.frame_y = mouse_y

    def normalize(self):
        return (min(self.start_x, self.end_x),
                min(self.start_y, self.end_y),
                max(self.start_x, self.end_x),
                max(self.start_y, self.end_y))

    def apply(self):
        super().apply()

        (x1, y1, x2, y2) = self.normalize()
        self.layer.x1 = x1
        self.layer.y1 = y1
        self.layer.x2 = x2
        self.layer.y2 = y2
        self.layer.update()

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            width = doc.imageSurface.get_width()
            height = doc.imageSurface.get_height()

            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, width, self.start_y)
            cr.rectangle(0, 0, self.start_x, height)
            cr.rectangle(mouse_x, 0, mouse_x, height)
            cr.rectangle(0, mouse_y, width, mouse_y)
            cr.fill()

    def width(self):
        return abs(int(self.end_x - self.start_x))

    def height(self):
        return abs(int(self.end_y - self.start_y))
        
class PathAnnotationTool(Tool):

    def __init__(self, document, layer=None):
        super().__init__(document, reticule = True)

        self._drawing = False

        self.layer = layer
        if layer == None:
            self.layer = PathAnnotationLayer(document)
            self.document.add_layer(self.layer)

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if not self._drawing:
            self.layer.points = []
            self.layer.points.append((mouse_x, mouse_y))
            self._drawing = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        if self._drawing:
            self.layer.points.append((mouse_x, mouse_y))

        self._drawing = False

    def mouse_move(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_move(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.points.append((mouse_x, mouse_y))

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.draw(w, cr)

class ImageAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = ImageAnnotationLayer(document)
            self.document.add_layer(self.layer)

    def cancel(self):
        super().cancel()

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y, mouse_button):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y, mouse_button)

        # ask for the image at first
        self.layer.ask_for_image_if_needed()

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing or self._moving:
            (x1, y1, x2, y2) = self.normalize()
            self.layer.x1 = x1
            self.layer.y1 = y1
            self.layer.x2 = x2
            self.layer.y2 = y2
            self.layer.draw(w, cr)
