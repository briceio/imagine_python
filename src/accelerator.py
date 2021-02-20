from gi.repository import Gdk
from threading import Thread
from gi.repository import GLib
from time import sleep, time

class Accelerator:

    ACTIVATION_TIMEOUT = 1.0

    def __init__(self, activation_key=Gdk.KEY_Tab, activation_timeout=1.0):
        self.activation_key = activation_key
        self.activation_timeout = activation_timeout
        self.contexts = {}
        self.commands = {}
        self.buffer = []
        self.disable()

        print("Acceleration activation key: %d" % self.activation_key)
        print("Acceleration activation timeout: %f" % self.activation_timeout)

        # TODO check singleton

        # init
        self.action_pending = False

        # start the accelerator
        self.running = True
        self.thread = Thread(target=self._thread, args=())
        self.thread.start()

    def key_handler(self, widget, event):
        if not self.enabled:
            return

        if not self.action_pending and event.keyval == self.activation_key:
            self.last_action_time = time()
            self.buffer = []
            self.action_pending = True
            return True
        elif self.action_pending:
            self.last_action_time = time()
            self.buffer.append(event.keyval)
            self._process_buffer()
            return True

    def stop(self):
        self.running = False # to stop the thread

    def _thread(self):
        print("Accelerator thread started.")

        while (self.running):
            # disable action if too much time spent
            if self.action_pending:
                delta = time() - self.last_action_time
                if delta >= self.activation_timeout:
                    self.action_pending = False

            sleep(0.25)

        print("Accelerator thread killed successfully.")

    def _process_buffer(self):
        for _, (command, action) in enumerate(self._current_context.items()):

            # parse command
            codes = list(map(lambda c: ord(c), command.split(",")))

            if len(self.buffer) == len(codes):
                valid = True
                for i, j in zip(self.buffer, codes):
                    if i != j:
                        valid = False
                        break

                if valid:
                    self.buffer = []
                    self.action_pending = False
                    self._execute_action(command, action)
                    break

    def _execute_action(self, command, action):
        print("Acceleration action triggered: %s" % command)

        if callable(action):
            GLib.idle_add(lambda: action())

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

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
