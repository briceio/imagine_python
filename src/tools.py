class Tool:

    def __init__(self, **args):
        self.reticule = bool(args["reticule"]) if "reticule" in args else False

    def mouse_down(self, w, cr, mouse_x, mouse_y):
        pass

    def mouse_up(self, w, cr, mouse_x, mouse_y):
        pass

    def draw(self, w, cr, mouse_x, mouse_y):

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
    _start_x = 0
    _start_y = 0

    def __init__(self):
        super().__init__(reticule = True)

    def mouse_down(self, w, cr, mouse_x, mouse_y):
        super().mouse_down(w, cr, mouse_x, mouse_y)
        if not self._drawing:
            self._start_x = mouse_x
            self._start_y = mouse_y
            self._drawing = True

    def mouse_up(self, w, cr, mouse_x, mouse_y):
        super().mouse_up(w, cr, mouse_x, mouse_y)
        self._drawing = False

    def draw(self, w, cr, mouse_x, mouse_y):
        super().draw(w, cr, mouse_x, mouse_y)

        if self._drawing:
            cr.set_source_rgba(0, 0, 0, 0.5)
            cr.set_line_width(0)
            cr.set_dash([])
            cr.rectangle(0, 0, w.get_allocation().width, self._start_y)
            cr.rectangle(0, 0, self._start_x, w.get_allocation().height)
            cr.rectangle(mouse_x, 0, mouse_x, w.get_allocation().height)
            cr.rectangle(0, mouse_y, w.get_allocation().width, mouse_y)
            cr.fill()
