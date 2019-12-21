from __future__ import print_function
import argparse
import logging
import os
import random
import sys

import pygame
import signal

from orwell.client.joystick import Joystick
from orwell.client.runner import Runner

RUNNER = None
LOGGER = None


def parse():
    parser = argparse.ArgumentParser(description='Client.')
    parser.add_argument(
        '--connection',
        help='Provide connection parameters '
        '<ip>,<push_port>,<subscribe_port>,<replier_port>',
        default=None)
    parser.add_argument(
        '--no-joystick',
        help='Disable joystick handling',
        dest='joystick',
        default=True,
        action="store_false")
    parser.add_argument(
        '--verbose', '-v',
        help='Verbose mode',
        default=False,
        action="store_true")
    arguments = parser.parse_args()
    global LOGGER
    LOGGER = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    if (arguments.verbose):
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.INFO)
    from orwell.client import runner
    runner.configure_logging(arguments.verbose)
    if (arguments.joystick):
        from orwell.client import joystick
        joystick.configure_logging(arguments.verbose)
    LOGGER.debug("Return parsed arguments")
    return arguments


def build_runner(arguments, devices):
    if (arguments.connection):
        # commas = arguments.connection.count(',')
        ip, push_port, subscribe_port, replier_port = \
            arguments.connection.split(',', 4)
        runner = Runner(
                devices,
                push_address="tcp://{ip}:{port}".format(
                    ip=ip, port=push_port),
                subscribe_address="tcp://{ip}:{port}".format(
                    ip=ip, port=subscribe_port),
                replier_address="tcp://{ip}:{port}".format(
                    ip=ip, port=replier_port)
                )
    else:
        runner = Runner(devices)
    return runner


def main():
    global RUNNER
    global LOOGER
    random.seed(None)
    arguments = parse()
    # done = False
    devices = []
    if (arguments.joystick):
        LOGGER.debug("Joystick enabled")
        pygame.init()
        os.putenv('SDL_VIDEODRIVER', 'dummy')
        pygame.display.set_mode((1, 1))
        pygame.display.init()
        pygame.joystick.init()
        sensivity = 0.05
        joystick_count = pygame.joystick.get_count()
        if (joystick_count > 1):
            LOGGER.warning("Warning,", joystick_count, " joysticks detected")
        for i in range(joystick_count):
            LOGGER.debug("joystick " + str(i) + " start")
            joystick = pygame.joystick.Joystick(i)
            LOGGER.debug("joystick " + str(i) + " retrieved")
            joystick_wrapper = Joystick.get_joystick(joystick, sensivity)
            LOGGER.debug("joystick " + str(i) + " wrapper found")
            devices.append(joystick_wrapper)
        runner = build_runner(arguments, devices)
        RUNNER = runner
        runner.run()
        pygame.quit()
    else:
        LOGGER.debug("Joystick NOT enabled")
        from orwell.client import keyboard
        keyboard.configure_logging(arguments.verbose)
        devices.append(keyboard.Keyboard())
        LOGGER.debug("About to build runner")
        runner = build_runner(arguments, devices)
        LOGGER.debug("About to start runner")
        RUNNER = runner
        runner.run()


def signal_handler(signal, frame):
    global RUNNER
    LOGGER.info('You pressed Ctrl+C!')
    if (RUNNER):
        RUNNER.destroy()
    # let's hope it does nothing wrong if not initialised
    pygame.quit()
    sys.exit(0)


if ("__main__" == __name__):
    signal.signal(signal.SIGINT, signal_handler)
    main()
