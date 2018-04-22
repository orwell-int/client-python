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


def parse():
    parser = argparse.ArgumentParser(description='Client.')
    parser.add_argument(
        '--connection',
        help='Proved connection parameters <ip>,<push_port>,<subscribe_port>',
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
    log = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    if (arguments.verbose):
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    from orwell.client import runner
    runner.configure_logging(arguments.verbose)
    if (arguments.joystick):
        from orwell.client import joystick
        joystick.configure_logging(arguments.verbose)
    return arguments


def build_runner(arguments, devices):
    if (arguments.connection):
        ip, push_port, subscribe_port = arguments.connection.split(',', 3)
        runner = Runner(
                devices,
                push_address="tcp://{ip}:{port}".format(ip=ip, port=push_port),
                subscribe_address="tcp://{ip}:{port}".format(
                    ip=ip, port=subscribe_port))
    else:
        runner = Runner(devices)
    return runner

def main():
    global RUNNER
    random.seed(None)
    arguments = parse()
    # done = False
    devices = []
    if (arguments.joystick):
        pygame.init()
        os.putenv('SDL_VIDEODRIVER', 'dummy')
        pygame.display.set_mode((1, 1))
        pygame.display.init()
        pygame.joystick.init()
        sensivity = 0.05
        joystick_count = pygame.joystick.get_count()
        if (joystick_count > 1):
            logging.warning("Warning,", joystick_count, " joysticks detected")
        for i in range(joystick_count):
            logging.debug("joystick " + str(i) + " start")
            joystick = pygame.joystick.Joystick(i)
            logging.debug("joystick " + str(i) + " retrieved")
            joystick_wrapper = Joystick.get_joystick(joystick, sensivity)
            logging.debug("joystick " + str(i) + " wrapper found")
            devices.append(joystick_wrapper)
        runner = build_runner(arguments, devices)
        RUNNER = runner
        runner.run()
        pygame.quit()
    else:
        from orwell.client import keyboard
        keyboard.configure_logging(arguments.verbose)
        devices.append(keyboard.Keyboard())
        runner = build_runner(arguments, devices)
        RUNNER = runner
        runner.run()


def signal_handler(signal, frame):
    global RUNNER
    logging.info('You pressed Ctrl+C!')
    if (RUNNER):
        RUNNER.destroy()
    # let's hope it does nothing wrong if not initialised
    pygame.quit()
    sys.exit(0)

if ("__main__" == __name__):
    signal.signal(signal.SIGINT, signal_handler)
    main()
