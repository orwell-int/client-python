from __future__ import division
import logging

from pynput import keyboard

from orwell.client.device import Device
from orwell.client.input import Input


LOGGER = None


class KeyboardThread(object):
    def __init__(self):
        LOGGER.debug("KeyboardThread::__init__")
        self._left = False
        self._right = False
        self._enter = False
        self._space = False
        self._p = False
        # Collect events until released
        self._listener = keyboard.Listener(
            on_press=lambda x: self.on_press(x),
            on_release=lambda x: self.on_release(x))
        self._listener.start()

    def stop(self):
        self._listener.stop()

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

    @property
    def enter(self):
        return self._enter

    @property
    def space(self):
        return self._space

    @property
    def p(self):
        return self._p

    def on_press(self, key):
        LOGGER.debug("on_press({})".format(key))
        try:
            if (keyboard.Key.left == key):
                self._left = True
            elif (keyboard.Key.right == key):
                self._right = True
            elif (keyboard.Key.enter == key):
                self._enter = True
            elif (keyboard.Key.space == key):
                self._space = True
            elif (keyboard.KeyCode.from_char('p') == key):
                self._p = True
        except AttributeError:
            print('special key {0} pressed'.format(key))

    def on_release(self, key):
        LOGGER.debug("on_release({})".format(key))
        try:
            if (keyboard.Key.left == key):
                self._left = False
            elif (keyboard.Key.right == key):
                self._right = False
            elif (keyboard.Key.enter == key):
                self._enter = False
            elif (keyboard.Key.space == key):
                self._space = False
            elif (keyboard.KeyCode.from_char('p') == key):
                self._p = False
        except AttributeError:
            print('special key {0} released'.format(key))


# No test yet
class Keyboard(Device):
    def __init__(self):
        LOGGER.debug("Keyboard::__init__")
        self._left = False
        self._right = False
        self._fire_weapon1 = False
        self._fire_weapon2 = False
        self._ping = False
        self._keyboard_thread = KeyboardThread()
        self._has_new_values = False

    def process(self):
        left = self._keyboard_thread.left
        if (self._left != left):
            self._has_new_values = True
            self._left = left
        right = self._keyboard_thread.right
        if (self._right != right):
            self._has_new_values = True
            self._right = right
        fire_weapon1 = self._keyboard_thread.enter
        if (self._fire_weapon1 != fire_weapon1):
            self._has_new_values = True
            self._fire_weapon1 = fire_weapon1
        fire_weapon2 = self._keyboard_thread.space
        if (self._fire_weapon2 != fire_weapon2):
            self._has_new_values = True
            self._fire_weapon2 = fire_weapon2
        ping = self._keyboard_thread.p
        if (ping):
            self._ping = True

    @property
    def has_new_values(self):
        return self._has_new_values

    def build_input(self):
        return Input(
                self.left,
                self.right,
                self.fire_weapon1,
                self.fire_weapon2)

        def read_ping(self):
            if (self._ping):
                self._ping = False
                return True
            else:
                return False


def configure_logging(verbose):
    print("keyboard.configure_logging")
    global LOGGER
    LOGGER = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    if (verbose):
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.INFO)
    LOGGER.debug("keyboard.configure_logging -- done")
