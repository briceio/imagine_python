from gi.repository import Gtk, Gdk, GObject

from .layers import Layer, Font

class LayerEditor(Gtk.ListBox):
    __gtype_name__ = 'LayerEditor'

    # called when the layer is updated
    on_update = None

    def __init__(self, layer, **kwargs):
        super().__init__(**kwargs)
        self.layer = layer
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self._build_ui()
        self._fields_before_modifications = {}

    def _build_ui(self):
        switcher = {
            "gchararray": self._build_string_editor,
            "gint": self._build_int_editor,
            "GdkRGBA": self._build_color_editor,
            "gboolean": self._build_checkbox_editor,
            "gdouble": self._build_double_editor,
            "imagine+layers+Font": self._build_font_editor,
            "imagine+layers+Selector": self._build_selector,
        }

        # order the properties
        ordered = {}
        not_ordered = []
        property_blurbs = {}

        for p in self.layer.list_properties():

            if p.nick != "":

                # parse blurbs
                blurbs = {}
                if p.blurb != None:
                    parts = p.blurb.split(";")
                    if len(parts) >= 1:
                        for part in parts:
                            if part.strip() != "":
                                key, value = part.split("=")
                                blurbs[key] = value
                property_blurbs[p] = blurbs # avoid double parsing

                # check for a order
                order = int(blurbs.get("order", -1))
                if order >= 0:
                    if ordered.get(order) != None:
                        print("Warning, order conflict: %d in property: %s" % (order, p.name))

                    ordered[order] = p
                else:
                    not_ordered.append(p)

        # build up widgets
        for p_key in sorted(ordered):
            p = ordered[p_key]
            switcher[p.value_type.name](p, property_blurbs.get(p, {}))

        for p in not_ordered:
            switcher[p.value_type.name](p, property_blurbs.get(p, {}))

        self.show_all()

    def _build_property_editor(self, p):
        box = Gtk.HBox()
        box.set_homogeneous(True)
        box.set_focus_on_click(False)

        label = Gtk.Label(p.nick)
        label.set_size_request(80, 30)
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        label.set_margin_start(5)
        box.pack_start(label, True, True, 0) # property label

        self.add(box)
        return box

    def _build_string_editor(self, p, blurbs):

        def on_change_file_entry(entry):
            self.layer.set_property(p.name, entry.get_filename())

        def block_event(widget, event):
            if not widget.has_focus():
                widget.grab_focus()
                return True
            return False

        box = self._build_property_editor(p)
        entry_type = blurbs.get("type", None)

        if entry_type == "multiline":
            scroll = Gtk.ScrolledWindow()
            scroll.set_hexpand(True)
            scroll.set_vexpand(True)

            entry = Gtk.TextView()
            entry.get_buffer().set_text(self.layer.get_property(p.name))
            entry.set_editable(True)
            entry.set_focus_on_click(True)
            box.set_size_request(-1, 75)

            entry.connect("button-press-event", block_event) # hack bug mouse click when textview in box
            self.layer.bind_property(p.name, entry.get_buffer(), "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
            scroll.add(entry);
            self._bind_history(p, entry) # history
            box.pack_start(scroll, True, True, 0)
        elif entry_type == "file":
            entry = Gtk.FileChooserButton()
            entry.set_title(p.nick)
            entry.connect("file-set", on_change_file_entry)
            self.layer.connect("notify::path", lambda w, p: entry.set_filename(self.layer.get_property(p.name)))
            box.pack_start(entry, True, True, 0)
        else:
            entry = Gtk.Entry()
            entry.set_text(self.layer.get_property(p.name))
            self.layer.bind_property(p.name, entry, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
            self._bind_history(p, entry) # history
            box.pack_start(entry, True, True, 0)

    def _bind_history(self, p, widget):
        capture_layer_name = self.layer.name

        def entry_history_before(widget, event):
            self._fields_before_modifications[widget] = widget.get_text()

        def entry_history_after(widget, event):
            old_text = self._fields_before_modifications.get(widget, None)
            new_text = widget.get_text()

            if old_text != None and old_text != new_text:
                self.layer.document.history.snapshot(
                    "Update layer %s attribute %s to %s" % (capture_layer_name, p.nick, new_text),
                    lambda: self.layer.set_property(p.name, old_text))

        def spinbutton_history_before(widget, event):
            self._fields_before_modifications[widget] = widget.get_value()

        def spinbutton_history_after(widget, event):
            old_text = self._fields_before_modifications.get(widget, None)
            new_text = round(widget.get_value(), widget.get_digits())

            if old_text != None and old_text != new_text:
                self.layer.document.history.snapshot(
                    "Update layer %s attribute %s to %s" % (capture_layer_name, p.nick, new_text),
                    lambda: self.layer.set_property(p.name, old_text))

        def textview_history_before(widget, event):
            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()
            self._fields_before_modifications[widget] = buffer.get_text(start, end, True)

        def textview_history_after(widget, event):
            old_text = self._fields_before_modifications.get(widget, None)

            buffer = widget.get_buffer()
            start, end = buffer.get_bounds()
            new_text = buffer.get_text(start, end, True)

            if old_text != None and old_text != new_text:
                self.layer.document.history.snapshot(
                    "Update layer %s attribute %s to %s" % (capture_layer_name, p.nick, new_text),
                    lambda: self.layer.set_property(p.name, old_text))

        def checkbutton_history(widget, before):
            after = widget.get_active()
            self.layer.document.history.snapshot(
                    "Switch layer %s attribute %s to %s" % (capture_layer_name, p.nick, after),
                    lambda: self.layer.set_property(p.name, before))

        if isinstance(widget, Gtk.SpinButton):
            widget.connect("focus-in-event", spinbutton_history_before)
            widget.connect("focus-out-event", spinbutton_history_after)
        elif isinstance(widget, Gtk.Entry):
            widget.connect("focus-in-event", entry_history_before)
            widget.connect("focus-out-event", entry_history_after)
        elif isinstance(widget, Gtk.TextView):
            widget.connect("focus-in-event", textview_history_before)
            widget.connect("focus-out-event", textview_history_after)
        elif isinstance(widget, Gtk.CheckButton):
            widget.connect("toggled", checkbutton_history, widget.get_active())

    def _build_int_editor(self, p, blurbs):

        box = self._build_property_editor(p)
        entry = Gtk.SpinButton()
        entry.set_range(p.minimum, p.maximum)

        # steps
        step1 = int(blurbs.get("step1", 1))
        step2 = int(blurbs.get("step2", 1))
        entry.set_increments(step1, step2)
        self.layer.bind_property(p.name, entry, "value", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self._bind_history(p, entry) # history
        box.pack_start(entry, True, True, 0)

    def _build_double_editor(self, p, blurbs):

        box = self._build_property_editor(p)
        entry = Gtk.SpinButton()
        entry.set_range(p.minimum, p.maximum)
        entry.set_increments(0.1, 1.0)
        entry.set_digits(2)
        self.layer.bind_property(p.name, entry, "value", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self._bind_history(p, entry) # history
        box.pack_start(entry, True, True, 0)

    def _build_color_editor(self, p, blurbs):
        capture_layer_name = self.layer.name
        capture_old_color = self.layer.get_property(p.name)

        def on_change(entry):

            self.layer.document.history.snapshot(
                    "Change color of %s property %s" % (capture_layer_name, p.nick),
                    lambda: self.layer.set_property(p.name, capture_old_color))

            self.layer.set_property(p.name, entry.get_rgba())
            self.layer.notify(p.name)

        box = self._build_property_editor(p)
        entry = Gtk.ColorButton()
        entry.set_rgba(self.layer.get_property(p.name))
        entry.set_use_alpha(True)
        entry.connect("color-set", on_change)
        box.pack_start(entry, True, True, 0)

    def _build_checkbox_editor(self, p, blurbs):

        box = self._build_property_editor(p)
        entry = Gtk.CheckButton()
        self.layer.bind_property(p.name, entry, "active", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self._bind_history(p, entry) # history
        box.pack_start(entry, True, True, 0)

    def _build_font_editor(self, p, blurbs):
        capture_layer_name = self.layer.name
        font = self.layer.get_property(p.name)
        size = bool(blurbs.get("size", True))

        def on_change(entry):
            after = entry.get_font_name()

            self.layer.document.history.snapshot(
                    "Change font of %s property %s to %s" % (capture_layer_name, p.nick, after),
                    lambda: self.layer.set_property(p.name, font))

            self.layer.set_property(p.name, Font(after))
            self.layer.notify(p.name)

        box = self._build_property_editor(p)
        entry = Gtk.FontButton()
        entry.set_use_size(size)
        entry.set_show_size(size)
        entry.set_show_style(True)
        entry.set_font_name(font.desc)
        entry.connect("font-set", on_change)
        box.pack_start(entry, True, True, 0)

    def _build_selector(self, p, blurbs):
        box = self._build_property_editor(p)
        selector = self.layer.get_property(p.name)

        def on_change(entry):
            selector.index = int(entry.get_active())
            self._notify(p.name)

        combo = Gtk.ComboBoxText()
        for i, option in enumerate(selector.options):
            combo.append(str(i), option)
        combo.set_active(selector.index)
        combo.connect("changed", on_change)

        box.pack_start(combo, True, True, 0)
