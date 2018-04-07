from __future__ import print_function
import random
import sys
import logging
import datetime
import time

import pygame
import signal

import zmq

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.server_game_pb2 as pb_server_game
import orwell.messages.server_game_pb2 as pb_robot
from orwell.client.broadcast import Broadcast
from orwell.client.joystick import Joystick

global NAME
NAME = "client"


class MessageWrapper(object):
    def __init__(self, message):
        recipient, message_type, payload = message.split(' ', 2)
        self._recipient = recipient
        self._message_type = message_type
        self._payload = payload

    @property
    def recipient(self):
        return self._recipient

    @property
    def message_type(self):
        return self._message_type

    @property
    def payload(self):
        return self._payload

    def __str__(self):
        return "(message, recipient = " + self._recipient + \
            "; message_type = " + self._message_type + ")"


class Toto(object):
    STATE_INIT = "STATE_INIT"
    STATE_HELLO_SENT = "STATE_HELLO_SENT"
    STATE_WELCOME = "STATE_WELCOME"
    STATE_HELLO_SENT_READY = "STATE_HELLO_SENT_READY"
    STATE_WAITING_GAME_START = "STATE_WAITING_GAME_START"
    STATE_GAME_RUNNING = "STATE_GAME_RUNNING"

    def __init__(self, push_address=None, subscribe_address=None):
        if ((push_address is None) or (subscribe_address is None)):
            broadcast = Broadcast()
            logging.info(broadcast.push_address +
                    " / " + broadcast.subscribe_address)
            self._push_address = broadcast.push_address
            self._subscribe_address = broadcast.subscribe_address
        else:
            self._push_address = push_address
            self._subscribe_address = subscribe_address
        self._context = zmq.Context.instance()
        self._push_socket = self._context.socket(zmq.PUSH)
        self._push_socket.setsockopt(zmq.LINGER, 0)
        self._push_socket.connect(self._push_address)
        self._subscribe_socket = self._context.socket(zmq.SUB)
        self._subscribe_socket.setsockopt(zmq.LINGER, 0)
        self._subscribe_socket.connect(self._subscribe_address)
        self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, "")
        self._routing_id = "temporary_id_" + str(random.randint(0, 32768))
        self._robot = None
        self._team = None
        self._abort = False
        self._state = Toto.STATE_INIT

    def destroy(self):
        self._push_socket.disconnect(self._push_address)
        self._push_socket.close()
        self._subscribe_socket.disconnect(self._subscribe_address)
        self._subscribe_socket.close()
        self._context.destroy()

    def start(self):
        assert(Toto.STATE_INIT == self._state)
        hello = self._build_hello(True)
        logging.info("send hello: ", repr(hello))
        self._push_socket.send(hello)
        self._state = Toto.STATE_HELLO_SENT

    def process(self):
        message_wrapper = self._receive()
        if (message_wrapper is None):
            return
        logging.debug(self._state + " | " + str(message_wrapper))
        if (("Pong" == message_wrapper.message_type) and
                (self._routing_id == message_wrapper.recipient)):
            self._decode_pong(message_wrapper)
        if (Toto.STATE_HELLO_SENT == self._state):
            if (self._routing_id == message_wrapper.recipient):
                self._decode_hello_reply(message_wrapper)
        elif (Toto.STATE_WELCOME == self._state):
            self._decode_game_state_init(message_wrapper)
        elif (Toto.STATE_HELLO_SENT_READY == self._state):
            self._decode_hello_reply_ready(message_wrapper)
        elif (Toto.STATE_WAITING_GAME_START):
            self._decode_game_state_start(message_wrapper)
        elif (Toto.STATE_GAME_RUNNING):
            self._decode_game_state_running(message_wrapper)

    def _receive(self):
        try:
            #message = self._subscribe_socket.recv()
            message = self._subscribe_socket.recv(zmq.NOBLOCK)
            if (message):
                message_wrapper = MessageWrapper(message)
                if (message_wrapper.recipient in
                        ("all_clients", self._routing_id)):
                    return message_wrapper
        except zmq.Again as e:
            logging.debug("no message")
            pass
        return None

    def _build_hello(self, ready):
        pb_message = pb_controller.Hello()
        name = "JAMBON"
        pb_message.name = name
        pb_message.ready = ready
        payload = pb_message.SerializeToString()
        return self._routing_id + ' Hello ' + payload

    def _decode_pong(self, message_wrapper):
        logging.debug("_decode_pong")
        message = pb_robot.Pong()
        message.ParseFromString(message_wrapper.payload)
        logging.info(
                "Pong ; id = " + str(message.id) +
                " ; len(timing) = " + len(message.timing))
        global NAME
        for timing in message.timing:
            timestamp = timing.timestamp
            if (NAME == timing.logger):
                ts = time.mktime(datetime.datetime.now().timetuple())
                elapsed = int(ts) - timestamp
            else:
                elapsed = timing.elapsed
            logging.info("'{logger}': @{timestamp} for {elapsed}".format(
                logger=timing.logger,
                timestamp=timestamp,
                elapsed=elapsed))

    def _decode_hello_reply(self, message_wrapper):
        logging.debug("_decode_hello_reply", message_wrapper.message_type)
        if ("Welcome" == message_wrapper.message_type):
            self._handle_welcome(message_wrapper.payload)
        elif ("Goodbye" == message_wrapper.message_type):
            self._handle_goodbye(message_wrapper.payload)
        else:
            logging.debug("Wrong message type: " + message_wrapper.message_type)

    def _decode_hello_reply_ready(self, message_wrapper):
        if ("Welcome" == message_wrapper.message_type):
            self._handle_welcome_ready(message_wrapper.payload)
        elif ("Goodbye" == message_wrapper.message_type):
            self._handle_goodbye(message_wrapper.payload)
        else:
            logging.debug("Wrong message type: " + message_wrapper.message_type)

    def _handle_welcome(self, payload):
        message = pb_server_game.Welcome()
        message.ParseFromString(payload)
        logging.info(
                "Welcome ; id = " + str(message.id) +
                " ; robot = '" + message.robot + "'" +
                " ; team = '" + message.team + "'")
        self._robot = message.robot
        self._team = message.team
        self._routing_id = str(message.id)
        self._state = Toto.STATE_WELCOME
        if (message.game_state):
            self._check_start_game(message.game_state)

    def _handle_welcome_ready(self, payload):
        message = pb_server_game.Welcome()
        message.ParseFromString(payload)
        logging.info(
                "Welcome [ready] ; id = " + str(message.id) +
                " ; robot = '" + message.robot + "'" +
                " ; team = '" + message.team + "'")
        self._robot = message.robot
        self._team = message.team
        self._routing_id = str(message.id)
        if (message.game_state):
            self._check_start_game(message.game_state)
        else:
            self._state = Toto.STATE_WAITING_GAME_START

    def _configure(self, game_state):
        logging.info("playing ? " + str(game_state.playing))
        logging.info("time left: " + str(game_state.seconds))
        # self._update_running(game_state.playing)
        for team in game_state.teams:
            logging.info(team.name + " (" + str(team.num_players) +
                        ") -> " + str(team.score))
        # let's assume we configure the different visualisations now
        self._push_socket.send(self._build_hello(True))
        self._state = Toto.STATE_HELLO_SENT_READY

    def _check_start_game(self, game_state):
        logging.info("_check_start_game: ", game_state.playing)
        if (game_state.playing):
            self._state = Toto.STATE_GAME_RUNNING
        else:
            self._state = Toto.STATE_WAITING_GAME_START

    def _decode_game_state_init(self, message_wrapper):
        if ("GameState" == message_wrapper.message_type):
            message = pb_server_game.GameState()
            message.ParseFromString(message_wrapper.payload)
            self._configure(message)

    def _decode_game_state_start(self, message_wrapper):
        if ("GameState" == message_wrapper.message_type):
            message = pb_server_game.GameState()
            message.ParseFromString(message_wrapper.payload)
            self._check_start_game(message)

    def _decode_game_state_running(self, message_wrapper):
        if ("GameState" == message_wrapper.message_type):
            message = pb_server_game.GameState()
            message.ParseFromString(message_wrapper.payload)
            self._update_visualisations(message)

    def _update_visualisations(self, game_state):
        logging.info("Updating visualisations")
        if (not game_state.running):
            self._state = Toto.STATE_WAITING_GAME_START

    def _handle_goodbye(self, payload):
        message = pb_server_game.Goodbye()
        message.ParseFromString(payload)
        logging.info("Goodbye ...")
        self._abort = True

    def send_input(self, joystick):
        if (joystick.has_new_values):
            pb_input = pb_controller.Input()
            pb_input.move.left = joystick.left
            pb_input.move.right = joystick.right
            pb_input.fire.weapon1 = joystick.fire_weapon1
            pb_input.fire.weapon2 = joystick.fire_weapon2
            payload = pb_input.SerializeToString()
            message = self._routing_id + ' Input ' + payload
            logging.debug("message sent: " + repr(message))
            self._push_socket.send(message)
            if (joystick.ping):
                pb_ping = pb_controller.Ping()
                timing_event = pb_ping.timing.add()
                global NAME
                timing_event.logger = NAME
                ts = time.mktime(datetime.datetime.now().timetuple())
                timestamp = int(ts)
                timing_event.timestamp = timestamp
                payload = pb_ping.SerializeToString()
                message = self._routing_id + ' Ping ' + payload
                logging.debug("message sent: " + repr(message))
                self._push_socket.send(message)


global TOTO
TOTO = None


def main():
    random.seed(None)
    #toto = Toto("tcp://localhost:9001", "tcp://localhost:9000")
    toto = Toto()
    global TOTO
    TOTO = toto
    toto.start()
    done = False
    pygame.init()
    os.putenv('SDL_VIDEODRIVER', 'dummy')
    pygame.display.set_mode((1,1))
    pygame.display.init()
    pygame.joystick.init()
    sensivity = 0.05
    k = 0
    while not done:
        if (0 == k % 100):
            print(k)
        k += 1
        for event in pygame.event.get(0.01):
            if event.type == pygame.JOYBUTTONDOWN:
                logging.debug("Joystick button pressed.")
            if event.type == pygame.JOYBUTTONUP:
                logging.debug("Joystick button released.")
            elif event.type == pygame.KEYDOWN:
                logging.debug("Key down:", event.key)
                if event.key == pygame.K_ESCAPE:
                    done = True
        joystick_count = pygame.joystick.get_count()
        if (joystick_count > 1):
            logging.warning("Warning,", joystick_count, " joysticks detected")
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            if not joystick.get_init():
                joystick.init()
            joystick_wrapper = Joystick.get_joystick(joystick, sensivity)
            joystick_wrapper.process()
            # print("left =", joystick_wrapper.left, "; right =", joystick_wrapper.right)
            #print(joystick_wrapper.right)
            #print(joystick_wrapper.fire_weapon1)
            #print(joystick_wrapper.fire_weapon2)
            toto.send_input(joystick_wrapper)

        toto.process()
    pygame.quit()


def signal_handler(signal, frame):
    logging.info('You pressed Ctrl+C!')
    global TOTO
    TOTO.destroy()
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
    main()
