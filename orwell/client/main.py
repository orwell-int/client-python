from __future__ import print_function
import exceptions
import random

import zmq

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.server_game_pb2 as pb_server_game
from orwell.client.broadcast import Broadcast
from orwell.client.joystick import Joystick


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
            print(broadcast.push_address + " / " + broadcast.subscribe_address)
            self._push_address = broadcast.push_address
            self._subscribe_address = broadcast.subscribe_address
        else:
            self._push_address = push_address
            self._subscribe_address = subscribe_address
        self._context = zmq.Context.instance()
        self._push_socket = self._context.socket(zmq.PUSH)
        self._push_socket.connect(self._push_address)
        self._subscribe_socket = self._context.socket(zmq.SUB)
        self._subscribe_socket.connect(self._subscribe_address)
        self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, "")
        self._routing_id = "temporary_id_" + str(random.randint(0, 32768))
        self._robot = None
        self._team = None
        self._abort = False
        self._state = Toto.STATE_INIT

    def start(self):
        assert(Toto.STATE_INIT == self._state)
        hello = self._build_hello(False)
        print("send hello: ", repr(hello))
        self._push_socket.send(hello)
        self._state = Toto.STATE_HELLO_SENT

    def process(self):
        message_wrapper = self._receive()
        if (message_wrapper is None):
            return
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
        message = self._subscribe_socket.recv()
        if (message):
            message_wrapper = MessageWrapper(message)
            if (message_wrapper.recipient in ("all_client", self._routing_id)):
                return message_wrapper
        return None

    def _build_hello(self, ready):
        pb_message = pb_controller.Hello()
        name = "JAMBON"
        pb_message.name = name
        pb_message.ready = ready
        payload = pb_message.SerializeToString()
        return self._routing_id + ' Hello ' + payload

    def _decode_hello_reply(self, message_wrapper):
        if ("Welcome" == message_wrapper.message_type):
            self._handle_welcome(message_wrapper.payload)
        elif ("Goodbye" == message_wrapper.message_type):
            self._handle_goodbye(message_wrapper.payload)
        else:
            pass
            # raise exceptions.NameError(
            #         "Wrong message type: " + message_wrapper.message_type)

    def _decode_hello_reply_ready(self, message_wrapper):
        if ("Welcome" == message_wrapper.message_type):
            self._handle_welcome_ready(message_wrapper.payload)
        elif ("Goodbye" == message_wrapper.message_type):
            self._handle_goodbye(message_wrapper.payload)
        else:
            pass
            # raise exceptions.NameError(
            #         "Wrong message type: " + message_wrapper.message_type)

    def _handle_welcome(self, payload):
        message = pb_server_game.Welcome()
        message.ParseFromString(payload)
        print("Welcome ; id = " + str(message.id) +
              " ; robot = '" + message.robot + "'" +
              " ; team = '" + message.team + "'")
        self._robot = message.robot
        self._team = message.team
        self._routing_id = str(message.id)
        if (message.game_state):
            self._configure(message.game_state)
        else:
            self._state = Toto.STATE_WELCOME

    def _handle_welcome_ready(self, payload):
        message = pb_server_game.Welcome()
        message.ParseFromString(payload)
        print("Welcome ; id = " + str(message.id) +
              " ; robot = '" + message.robot + "'" +
              " ; team = '" + message.team + "'")
        if (message.game_state):
            self._check_start_game(message.game_state)
        else:
            self._state = Toto.STATE_WAITING_GAME_START

    def _configure(self, game_state):
        print("playing ? " + str(game_state.playing))
        print("time left: " + str(game_state.seconds))
        # self._update_running(game_state.playing)
        for team in game_state.teams:
            print(team.name + " (" + str(team.num_players) +
                  ") -> " + str(team.score))
        # let's assume we configure the different visualisations now
        self._push_socket.send(self._build_hello(True))
        self._state = Toto.STATE_HELLO_SENT_READY

    def _check_start_game(self, game_state):
        if (game_state.playing):
            self._state = Toto.STATE_GAME_RUNNING

    def _decode_game_state_init(self, message_wrapper):
        if ("GameState" == message_wrapper.message_type):
            self._configure(message_wrapper.payload)

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
        print("Updating visualisations")
        if (not game_state.running):
            self._state = Toto.STATE_WAITING_GAME_START

    def _handle_goodbye(self, payload):
        message = pb_server_game.Goodbye()
        message.ParseFromString(payload)
        print("Goodbye ...")
        self._abort = True

    def send_input(self, joystick):
        pb_input = pb_controller.Input()
        pb_input.move.left = joystick.left
        pb_input.move.right = joystick.right
        pb_input.fire.weapon1 = joystick.fire_weapon1
        pb_input.fire.weapon2 = joystick.fire_weapon2
        payload = pb_input.SerializeToString()
        message = self._routing_id + ' Input ' + payload
        self._push_socket.send(message)


def main():
    random.seed(None)
    #toto = Toto("tcp://localhost:9001", "tcp://localhost:9000")
    toto = Toto()
    toto.start()
    done = False
    import pygame
    import time
    import os
    pygame.init()
    os.putenv('SDL_VIDEODRIVER', 'dummy')
    pygame.display.set_mode((1,1))
    pygame.display.init()
    pygame.joystick.init()
    sensivity = 0.05
    if False:
        while not done:
            for event in pygame.event.get(10):
                if event.type == pygame.JOYBUTTONDOWN:
                    print("Joystick button pressed.")
                if event.type == pygame.JOYBUTTONUP:
                    print("Joystick button released.")
            joystick_count = pygame.joystick.get_count()
            print(joystick_count, " joystick(s) detected")
            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                if not joystick.get_init():
                    joystick.init()
                print(" ", i, joystick.get_name())
                axes = joystick.get_numaxes()
                print("Number of axes: {}".format(axes))
                for i in range(axes):
                    axis = joystick.get_axis(i)
                    print("axis", i, "=", axis)
                buttons = joystick.get_numbuttons()
                print("Number of axes: {}".format(buttons))
                for i in range(buttons):
                    button = joystick.get_button(i)
                    print("button", i, "=", button)
            time.sleep(1)
    while not done:
        for event in pygame.event.get(10):
            if event.type == pygame.JOYBUTTONDOWN:
                print("Joystick button pressed.")
            if event.type == pygame.JOYBUTTONUP:
                print("Joystick button released.")
        joystick_count = pygame.joystick.get_count()
        if (joystick_count > 1):
            print("Warning,", joystick_count, " joysticks detected")
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            if not joystick.get_init():
                joystick.init()
            joystick_wrapper = Joystick(sensivity, joystick)
            joystick_wrapper.process()
            # print("left =", joystick_wrapper.left, "; right =", joystick_wrapper.right)
            #print(joystick_wrapper.right)
            #print(joystick_wrapper.fire_weapon1)
            #print(joystick_wrapper.fire_weapon2)
            toto.send_input(joystick_wrapper)

        toto.process()
        #time.sleep(1)

if ("__main__" == __name__):
    main()
