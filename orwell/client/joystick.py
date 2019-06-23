from __future__ import division
import math
from enum import Enum
import logging

import pygame

from orwell.client.device import Device
from orwell.client.input import Input

XINPUT = "xinput"
T_FLIGHT_HOTAS_X = "T.Flight Hotas X"
LOGGER = None


class JoystickType(Enum):
    xinput = 1
    t_flight_hots_x = 2

    @staticmethod
    def build(str_value):
        if (XINPUT in str_value):
            return JoystickType.xinput
        else:
            assert(T_FLIGHT_HOTAS_X in str_value)
            return JoystickType.t_flight_hots_x


# No test yet
class Joystick(Device):
    ANGLE_MIN = 0.0
    ANGLE_MAX = math.pi * 0.5

    JOYSTICKS = {}

    @classmethod
    def get_joystick(
            cls,
            pygame_joystick,
            dead_zone,
            angle=math.pi * 0.25,
            precision=0.025):
        LOGGER.debug("get_joystick IN")
        if (pygame_joystick.get_name() in cls.JOYSTICKS.keys()):
            joystick = cls.JOYSTICKS[pygame_joystick.get_name()]
            LOGGER.debug("get_joystick OUT memo")
            return joystick
        else:
            joystick = Joystick(pygame_joystick, dead_zone, angle, precision)
            cls.JOYSTICKS[pygame_joystick.get_name()] = joystick
            LOGGER.debug("get_joystick OUT new")
            return joystick

    def __init__(
            self,
            pygame_joystick,
            dead_zone,
            angle,
            precision):
        assert(Joystick.ANGLE_MIN < angle < Joystick.ANGLE_MAX)
        self._dead_zone = dead_zone
        self._joystick_type = JoystickType.build(pygame_joystick.get_name())
        self._angle = angle
        self._invert_direction = -1
        self._precision = float(precision)
        self.left = 0
        self.right = 0
        self.fire_weapon1 = False
        self.fire_weapon2 = False
        self.start = False
        self._ping = False
        self._debug = False
        self._pygame_joystick = pygame_joystick
        self._previous_left = None
        self._previous_right = None
        self._previous_fire_weapon1 = None
        self._previous_fire_weapon2 = None
        self._previous_start = False
        self._has_new_values = False
        if (not pygame_joystick.get_init()):
            LOGGER.info("Initialise pygame joystick")
            pygame_joystick.init()
            LOGGER.debug("buttons: " + str(pygame_joystick.get_numbuttons()))
            LOGGER.debug("axes: " + str(pygame_joystick.get_numaxes()))

    def __del__(self):
        if (self._pygame_joystick.get_init()):
            self._pygame_joystick.quit()

    def _round(self, value):
        new_value = int(value / self._precision) * self._precision
        if (math.fabs(new_value) < self._dead_zone):
            new_value = 0
        return new_value

    def process(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print("Joystick button pressed.")
            if event.type == pygame.JOYBUTTONUP:
                print("Joystick button released.")
        x = -self._pygame_joystick.get_axis(0)
        # print("x = " + str(x))
        y = self._pygame_joystick.get_axis(1)
        # print("y = " + str(y))
        if (self._debug):
            if (self._pygame_joystick.get_button(2) != 0):
                # X
                self._angle -= 0.0001
                print("angle = " + str(self._angle))
            if (self._pygame_joystick.get_button(1) != 0):
                # B
                self._angle += 0.0001
                print("angle = " + str(self._angle))
            if (self._pygame_joystick.get_button(3) != 0):
                # Y
                self._toggle_direction()
        if (JoystickType.xinput == self._joystick_type):
            # Gamepad
            factor = self._invert_direction * self._pygame_joystick.get_axis(7)
            # print("factor = " + str(factor))
            # left button (not arrow)
            self.fire_weapon1 = (self._pygame_joystick.get_button(4) != 0)
            # left trigger
            self.fire_weapon2 = (self._pygame_joystick.get_button(6) != 0)
            self.start = (self._pygame_joystick.get_button(9) != 0)
        else:
            # HOTAS
            factor = -self._invert_direction * self._pygame_joystick.get_axis(2)
            # print("factor = " + str(factor))
            self.fire_weapon1 = (self._pygame_joystick.get_button(1) != 0)
            self.fire_weapon2 = (self._pygame_joystick.get_button(0) != 0)
            self.start = (self._pygame_joystick.get_button(11) != 0)
            if (self._pygame_joystick.get_button(3) != 0):
                self._ping = True
        self._convert(x, y, factor)
        self._has_new_values = (
                (self._previous_left != self.left) or
                (self._previous_right != self.right) or
                (self._previous_fire_weapon1 != self.fire_weapon1) or
                (self._previous_fire_weapon2 != self.fire_weapon2) or
                (self._previous_start != self.start))
        if (self._has_new_values):
            LOGGER.debug("has new value ? " + str(self._has_new_values))
        self._previous_left = self.left
        self._previous_right = self.right
        self._previous_fire_weapon1 = self.fire_weapon1
        self._previous_fire_weapon2 = self.fire_weapon2
        self._previous_start = self.start

    def _toggle_direction(self):
        self._invert_direction = -self._invert_direction

    def _convert(self, x, y, factor):
        cosine = math.cos(self._angle)
        sine = math.sin(self._angle)
        scale = (cosine + sine) * 0.5
        # print("x =", x, "; y =", y, "; factor =", factor)
        # print("cosine =", cosine, "; sine =", sine, "; scale =", scale)
        # print("x * cosine =", x * cosine, "; y * sine =", sine)
        big_left = self._round(factor * (
            x * cosine +
            y * sine) / scale)
        big_right = self._round(factor * (
            y * cosine -
            x * sine) / scale)
        # print("big_left =", big_left, "; big_right =", big_right)
        self.left = max(-1, min(
                1,
                big_left))
        self.right = max(-1, min(
                1,
                big_right))

    @property
    def has_new_values(self):
        return self._has_new_values

    def build_input(self):
        LOGGER.debug("build_input")
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
    global LOGGER
    print("joystick.configure_logging")
    LOGGER = logging.getLogger(__name__)
    LOGGER.propagate = False
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    if (verbose):
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.INFO)
