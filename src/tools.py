from .layers import RectangleAnnotationLayer, LineAnnotationLayer

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

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y):
        pass

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y):
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

        pass

class RectTool(Tool):

    def __init__(self, document):
        super().__init__(document, reticule = True)
        self._drawing = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def cancel(self):
        super().cancel()
        self._drawing = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y)
        if not self._drawing:
            self.start_x = mouse_x
            self.start_y = mouse_y
            self._drawing = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.end_x = mouse_x
            self.end_y = mouse_y
            self.apply()

        self._drawing = False

    def width(self):
        return int(self.end_x - self.start_x)

    def height(self):
        return int(self.end_y - self.start_y)

class LineTool(Tool):

    def __init__(self, document):
        super().__init__(document, reticule = True)
        self._drawing = False
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

    def cancel(self):
        super().cancel()
        self._drawing = False

    def mouse_down(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_down(doc, w, cr, mouse_x, mouse_y)
        if not self._drawing:
            self.start_x = mouse_x
            self.start_y = mouse_y
            self._drawing = True

    def mouse_up(self, doc, w, cr, mouse_x, mouse_y):
        super().mouse_up(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.end_x = mouse_x
            self.end_y = mouse_y
            self.apply()

        self._drawing = False

    def width(self):
        return int(self.end_x - self.start_x)

    def height(self):
        return int(self.end_y - self.start_y)

class CropTool(RectTool):

    def __init__(self, document):
        super().__init__(document)

    def apply(self):
        super().apply()
        self.document.crop(self.start_x, self.start_y, self.end_x, self.end_y)

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

class RectangleAnnotationTool(RectTool):

    def __init__(self, document, layer=None):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = RectangleAnnotationLayer()
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.x1 = self.start_x
            self.layer.y1 = self.start_y
            self.layer.x2 = mouse_x
            self.layer.y2 = mouse_y
            self.layer.draw(w, cr)

class LineAnnotationTool(LineTool):

    def __init__(self, document, layer=None, arrow=False):
        super().__init__(document)

        self.layer = layer
        if layer == None:
            self.layer = LineAnnotationLayer(arrow=arrow)
            self.document.add_layer(self.layer)

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            self.layer.x1 = self.start_x
            self.layer.y1 = self.start_y
            self.layer.x2 = mouse_x
            self.layer.y2 = mouse_y
            self.layer.draw(w, cr)
