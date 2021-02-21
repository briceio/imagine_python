from gi.repository import Gdk
from threading import Thread
from gi.repository import GLib, Gtk
from time import sleep, time

class Accelerator:

    ACTIVATION_TIMEOUT = 1.0

    def __init__(self, activation_timeout=1.0):
        self.activation_timeout = activation_timeout
        self.global_context = {}
        self.contexts = {}
        self.commands = {}
        self.buffer = []
        self.disable()
        self._current_context = None

        print("Acceleration activation timeout: %f" % self.activation_timeout)

        # TODO check singleton

        # init
        self.action_pending = False

        # start the accelerator
        self.running = True
        self.thread = Thread(target=self._thread, args=())
        self.thread.start()

    EXCLUDED_KEYVALS = [Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R]

    class Key:
        def __init__(self, key, mod):
            self.key = key
            self.mod = mod

    def key_handler(self, widget, event):

        def register_event():
            if event.type == Gdk.EventType.KEY_PRESS and not event.keyval in Accelerator.EXCLUDED_KEYVALS:
                self.buffer.append(Accelerator.Key(event.keyval, event.state))

        if not self.enabled:
            return

        print("Accelerator command: %s" % Gtk.accelerator_name_with_keycode(None, event.keyval, event.hardware_keycode, event.state))

        if not self.action_pending:
            self.action_pending = True
            self.buffer = []

        if self.action_pending:
            self.last_action_time = time()
            register_event()
            return self._process_buffer()

        return False

    def stop(self):
        self.running = False # to stop the thread

    def _thread(self):
        print("Accelerator thread started.")

        while (self.running):
            # disable action if too much time spent
            if self.action_pending:
                delta = time() - self.last_action_time
                if delta >= self.activation_timeout:
                    self.buffer = []
                    self.action_pending = False

            sleep(0.25)

        print("Accelerator thread killed successfully.")

    def _process_buffer(self):

        # merge global & current active contexts
        # to be replaced with A | B in Python 3.9+ (A |= B)
        contexts = self.global_context.copy()
        if self._current_context != None:
            contexts.update(self._current_context)

        for _, (command, action) in enumerate(contexts.items()):

            # parse command
            codes = command.split(",")

            if len(self.buffer) == len(codes):
                valid = True
                for event, accelerator in zip(self.buffer, codes):
                    key, mod = Gtk.accelerator_parse(accelerator)

                    if key != event.key or mod != event.mod:
                        valid = False
                        continue

                if valid:
                    self.buffer = []
                    self.action_pending = False
                    self._execute_action(command, action)
                    return True

        return False

    def _execute_action(self, command, action):
        print("Acceleration action triggered: %s" % command)

        if callable(action):
            GLib.idle_add(lambda: action())

    def add(self, context, command, action):
        if context == None:
            self.global_context[command] = action
        else:
            self.contexts.setdefault(context, {})[command] = action

    def set_context(self, context):
        if self.contexts.__contains__(context):
            self._current_context = self.contexts[context]
            print("Accelerator context set to: %s" % context)
        else:
            print("Unknown accelerator context: %s" % context)

    def trigger(self, command):
        if self.commands.__contains__(command):
            print("ok")
        else:
            print("Unknown accelerator command: %s" % command)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.buffer = []
        self.action_pending = False
        self.enabled = False
