from __future__ import print_function
import logging
import os
import random
import sys

import pygame
import signal

from orwell.client.joystick import Joystick
from orwell.client.runner import Runner

global NAME
NAME = "client"


global RUNNER
RUNNER = None


def main():
    random.seed(None)
    #runner = Runner("tcp://192.168.1.11:9001", "tcp://192.168.1.11:9000")
    runner = Runner()
    global RUNNER
    RUNNER = runner
    runner.start()
    done = False
    pygame.init()
    os.putenv('SDL_VIDEODRIVER', 'dummy')
    pygame.display.set_mode((1,1))
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
    k = 0
    while not done:
        if (0 == k % 10000):
            print(k)
        k += 1
        force_ping = False
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                logging.debug("Joystick button pressed.")
            if event.type == pygame.JOYBUTTONUP:
                logging.debug("Joystick button released.")
            elif event.type == pygame.KEYDOWN:
                logging.debug("Key down: " + str(event.key))
                if event.key == pygame.K_SPACE:
                    logging.debug("Forece ping")
                    force_ping = True
                elif event.key == pygame.K_ESCAPE:
                    done = True
        joystick_count = pygame.joystick.get_count()
        if (joystick_count > 1):
            logging.warning("Warning,", joystick_count, " joysticks detected")
        joystick_wrapper.process()
        # print("left =", joystick_wrapper.left, "; right =", joystick_wrapper.right)
        #print(joystick_wrapper.right)
        #print(joystick_wrapper.fire_weapon1)
        #print(joystick_wrapper.fire_weapon2)
        runner.send_input(joystick_wrapper, force_ping)

        runner.process()
    pygame.quit()


def signal_handler(signal, frame):
    logging.info('You pressed Ctrl+C!')
    global RUNNER
    RUNNER.destroy()
    pygame.quit()
    sys.exit(0)

if ("__main__" == __name__):
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    signal.signal(signal.SIGINT, signal_handler)
    from orwell.client import joystick
    joystick.configure_logging(True)
    main()
