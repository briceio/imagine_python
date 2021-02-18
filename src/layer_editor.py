from gi.repository import Gtk
from gi.repository import Gdk

from .layers import Layer

class LayerEditor(Gtk.ListBox):
    __gtype_name__ = 'LayerEditor'

    # called when the layer is updated
    on_update = None

    def __init__(self, layer, **kwargs):
        super().__init__(**kwargs)
        self.layer = layer
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self._build_ui()

    def _build_ui(self):
        switcher = {
            "gchararray": self._build_string_editor,
            "gint": self._build_int_editor,
        }

        # build properties editors
        for p in self.layer.list_properties():
            switcher[p.value_type.name](p)

        self.show_all()

    def _notify(self, p):
        #self.layer.notify(p) TODO DEBUG > model not updated: notify problem?
        if self.on_update != None:
            self.on_update(self.layer)

    def _build_property_editor(self, p):
        box = Gtk.HBox()
        box.pack_start(Gtk.Label(p.nick), True, True, 0) # property label
        self.add(box)
        return box

    def _build_string_editor(self, p):

        def on_change(entry):
            self.layer.set_property(p.name, entry.get_text())
            self._notify(p.name)

        box = self._build_property_editor(p)
        entry = Gtk.Entry()
        entry.set_text(self.layer.get_property(p.name))
        entry.connect("changed", on_change)
        box.pack_start(entry, True, True, 0)

    def _build_int_editor(self, p):

        def on_change(entry):
            self.layer.set_property(p.name, entry.get_value())
            self._notify(p.name)

        box = self._build_property_editor(p)
        entry = Gtk.SpinButton()
        entry.set_range(1, 100)
        entry.set_increments(1, 5)
        entry.set_value(self.layer.get_property(p.name))
        entry.connect("changed", on_change)
        box.pack_start(entry, True, True, 0)

