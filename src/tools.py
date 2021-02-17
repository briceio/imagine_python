class Tool:

    def __init__(self, callback, **args):
        self.callback = callback
        self.reticule = bool(args["reticule"]) if "reticule" in args else False

    def apply(self):
        if self.callback != None:
            self.callback(self)

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
            cr.line_to(mouse_x, w.get_allocation().height)

            cr.move_to(0, mouse_y)
            cr.line_to(w.get_allocation().width, mouse_y)

            cr.stroke()

        pass

class AreaSelector(Tool):

    _drawing = False
    start_x = 0
    start_y = 0
    end_x = 0
    end_y = 0

    def __init__(self, callback):
        super().__init__(callback, reticule = True)

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

    def draw(self, doc, w, cr, mouse_x, mouse_y):
        super().draw(doc, w, cr, mouse_x, mouse_y)

        if self._drawing:
            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, w.get_allocation().width, self.start_y)
            cr.rectangle(0, 0, self.start_x, w.get_allocation().height)
            cr.rectangle(mouse_x, 0, mouse_x, w.get_allocation().height)
            cr.rectangle(0, mouse_y, w.get_allocation().width, mouse_y)
            cr.fill()

    def width(self):
        return int(self.end_x - self.start_x)

    def height(self):
        return int(self.end_y - self.start_y)
    
