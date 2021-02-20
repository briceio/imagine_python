from gi.repository import Gdk
from .GObject_async import *

class Accelerator:

    ACTIVATION_TIMEOUT = 1.0

    def __init__(self, activation_key=Gdk.KEY_Tab):
        self.activation_key = activation_key
        self.contexts = {}
        self.commands = {}
        self.enabled = False
        print("Acceleration activation key: %d" % self.activation_key)

    def key_handler(self, widget, event):
        print("event: %s" % str(event.keyval))

        if not self.enabled and event.keyval == self.activation_key:
            self._enable()
            return True

    def add(self, context, command, action):
        self.contexts.setdefault(context, {})[command] = action
        print("Accelerator command '%s' added in context: %s" % (command, context))

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

    def _enable(self):
        print("Accelerator listening...")
        self.enabled = True
        self._disable()

    @delayed(ACTIVATION_TIMEOUT)
    def _disable(self):
        print("Accelerator disabled.")
        self.enabled = False
