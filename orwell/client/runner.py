import logging
import random
import time

import zmq

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.server_game_pb2 as pb_server_game
import orwell.messages.robot_pb2 as pb_robot

from orwell.client.broadcast import Broadcast
from orwell.client.message_wrapper import MessageWrapper

NAME = "client"
LOGGER = None


class Runner(object):
    STATE_INIT = "STATE_INIT"
    STATE_WELCOME = "STATE_WELCOME"
    STATE_WAITING_GAME_START = "STATE_WAITING_GAME_START"
    STATE_GAME_RUNNING = "STATE_GAME_RUNNING"

    def __init__(
            self,
            devices,
            push_address=None,
            subscribe_address=None,
            reply_address=None):
        self._devices = devices
        if ((push_address is None) or (subscribe_address is None)):
            broadcast = Broadcast()
            LOGGER.info(
                    broadcast.push_address +
                    " / " + broadcast.subscribe_address +
                    " / " + broadcast.reply_address)
            self._push_address = broadcast.push_address
            self._subscribe_address = broadcast.subscribe_address
            self._reply_address = broadcast.reply_address
        else:
            self._push_address = push_address
            self._subscribe_address = subscribe_address
            self._reply_address = reply_address
        self._context = zmq.Context.instance()
        self._push_socket = self._context.socket(zmq.PUSH)
        self._push_socket.setsockopt(zmq.LINGER, 0)
        self._push_socket.connect(self._push_address)
        self._subscribe_socket = self._context.socket(zmq.SUB)
        self._subscribe_socket.setsockopt(zmq.LINGER, 0)
        self._subscribe_socket.connect(self._subscribe_address)
        self._reply_socket = self._context.socket(zmq.REQ)
        self._reply_socket.setsockopt(zmq.LINGER, 0)
        self._reply_socket.connect(self._reply_address)
        self._routing_id = "temporary_id_" + str(random.randint(0, 32768))
        # at first we are only interested to messages specific to this client
        self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, self._routing_id)
        self._robot = None
        self._team = None
        self._abort = False
        self._state = Runner.STATE_INIT
        self._ping = False

    def destroy(self):
        self._push_socket.disconnect(self._push_address)
        self._push_socket.close()
        self._subscribe_socket.disconnect(self._subscribe_address)
        self._subscribe_socket.close()
        self._context.destroy()

    def start(self):
        assert(Runner.STATE_INIT == self._state)
        self._hello_and_reply(False)

    def run(self):
        self.start()
        k = 0
        while not self._abort:
            if (0 == k % 100000):
                print(k)
            k += 1
            for device in self._devices:
                device.process()

                if (Runner.STATE_GAME_RUNNING == self._state):
                    if (device.has_new_values):
                        msg = device.build_input().get_message(self._routing_id)
                        self._push_socket.send(msg)
                if (not self._ping):
                    if (device.read_ping()):
                        self._send_ping()
            self.process()

    def _send_ping(self):
        self._ping = True
        pb_ping = pb_controller.Ping()
        timing_event = pb_ping.timing.add()
        timing_event.logger = NAME
        timestamp = int(round(time.time() * 1000))
        timing_event.timestamp = timestamp
        payload = pb_ping.SerializeToString()
        message = self._routing_id + ' Ping ' + payload
        LOGGER.info("message sent: " + repr(message))
        self._push_socket.send(message)

    def process(self):
        message_wrapper = self._receive()
        if (message_wrapper is None):
            return
        LOGGER.debug("[process]" +  self._state + " | " + str(message_wrapper))
        if (("Pong" == message_wrapper.message_type) and
                (self._routing_id == message_wrapper.recipient)):
            self._decode_pong(message_wrapper)
        if (Runner.STATE_WELCOME == self._state):
            self._decode_game_state_init(message_wrapper)
        elif (Runner.STATE_WAITING_GAME_START == self._state):
            self._decode_game_state_start(message_wrapper)
        elif (Runner.STATE_GAME_RUNNING == self._state):
            self._decode_game_state_running(message_wrapper)

    def _receive(self):
        try:
            message = self._subscribe_socket.recv(zmq.NOBLOCK)
            if (message):
                return MessageWrapper(message)
        except zmq.Again:
            pass
        # except zmq.Again as e:
            # LOGGER.debug("no message: " + str(e))
        return None

    def _build_hello(self, ready):
        pb_message = pb_controller.Hello()
        name = "JAMBON"
        pb_message.name = name
        pb_message.ready = ready
        payload = pb_message.SerializeToString()
        return self._routing_id + ' Hello ' + payload

    def _decode_pong(self, message_wrapper):
        LOGGER.debug("_decode_pong")
        self._ping = False
        message = pb_robot.Pong()
        message.ParseFromString(message_wrapper.payload)
        LOGGER.info(
                "Pong ; len(timing) = " + str(len(message.timing)))
        for timing in message.timing:
            timestamp = timing.timestamp
            if (NAME == timing.logger):
                timestamp_now = int(round(time.time() * 1000))
                LOGGER.info("timestamp_now = " + str(timestamp_now))
                LOGGER.info("timestamp = " + str(timestamp))
                elapsed = timestamp_now - timestamp
            else:
                elapsed = timing.elapsed
            LOGGER.info("'{logger}': @{timestamp} for {elapsed}".format(
                logger=timing.logger,
                timestamp=timestamp,
                elapsed=elapsed))

    def _decode_hello_reply(self, message_wrapper, ready):
        LOGGER.debug("_decode_hello_reply " +
                      str(message_wrapper.message_type))
        if ("Welcome" == message_wrapper.message_type):
            self._handle_welcome(message_wrapper.payload, ready)
        elif ("Goodbye" == message_wrapper.message_type):
            self._handle_goodbye(message_wrapper.payload)
        else:
            LOGGER.debug("Wrong message type: " +
                          message_wrapper.message_type)

    def _handle_welcome(self, payload, ready):
        message = pb_server_game.Welcome()
        message.ParseFromString(payload)
        new_routing_id = str(message.id)
        LOGGER.info(
                "Welcome ; id = " + new_routing_id +
                " ; robot = '" + message.robot + "'" +
                " ; team = '" + message.team + "'")
        self._robot = message.robot
        self._team = message.team
        if (self._routing_id != new_routing_id):
            LOGGER.debug("update routing id to '" + new_routing_id + "'")
            # get rid of subscription to temporary routing id
            self._subscribe_socket.setsockopt(zmq.UNSUBSCRIBE, self._routing_id)
            self._routing_id = new_routing_id
            # and replace with subscription to given id
            self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, self._routing_id)
            # also listen to messages for all clients
            self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, "all_clients")
        if (message.game_state):
            LOGGER.debug("decode game state")
            self._check_start_game(message.game_state)
        elif (ready):
            self._state = Runner.STATE_WAITING_GAME_START
        else:
            self._state = Runner.STATE_WELCOME

    def _hello_and_reply(self, ready):
        hello = self._build_hello(ready)
        # print("send hello: " + repr(hello))
        LOGGER.info("send hello (ready=" + str(ready) + "): " + repr(hello))
        self._reply_socket.send(hello)
        reply = self._reply_socket.recv()
        message_wrapper = MessageWrapper(reply)
        self._decode_hello_reply(message_wrapper, ready)


    def _configure(self, game_state):
        LOGGER.info("playing ? " + str(game_state.playing))
        LOGGER.info("time left: " + str(game_state.seconds))
        # self._update_running(game_state.playing)
        for team in game_state.teams:
            LOGGER.info(team.name + " (" + str(team.num_players) +
                         ") -> " + str(team.score))
        # let's assume we configure the different visualisations now
        self._hello_and_reply(True)

    def _check_start_game(self, game_state):
        LOGGER.info("_check_start_game: " + str(game_state.playing))
        if (game_state.playing):
            self._state = Runner.STATE_GAME_RUNNING
        else:
            self._state = Runner.STATE_WAITING_GAME_START

    def _decode_game_state_init(self, message_wrapper):
        LOGGER.debug("_decode_game_state_init message is " + message_wrapper.message_type)
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
            if (not game_state.running):
                self._state = Runner.STATE_WAITING_GAME_START

    def _update_visualisations(self, game_state):
        LOGGER.info("Updating visualisations")

    def _handle_goodbye(self, payload):
        message = pb_server_game.Goodbye()
        message.ParseFromString(payload)
        LOGGER.info("Goodbye ...")
        self._state = Runner.STATE_INIT
        self._abort = True

    def send_input(self, joystick, force_ping):
        if (joystick.has_new_values):
            pb_input = pb_controller.Input()
            pb_input.move.left = joystick.left
            pb_input.move.right = joystick.right
            pb_input.fire.weapon1 = joystick.fire_weapon1
            pb_input.fire.weapon2 = joystick.fire_weapon2
            payload = pb_input.SerializeToString()
            message = self._routing_id + ' Input ' + payload
            LOGGER.debug("message sent: " + repr(message))
            self._push_socket.send(message)
            if (joystick.ping or force_ping):
                pb_ping = pb_controller.Ping()
                timing_event = pb_ping.timing.add()
                timing_event.logger = NAME
                timestamp = int(round(time.time() * 1000))
                timing_event.timestamp = timestamp
                payload = pb_ping.SerializeToString()
                message = self._routing_id + ' Ping ' + payload
                LOGGER.info("message sent: " + repr(message))
                self._push_socket.send(message)

def configure_logging(verbose):
    global LOGGER
    print("runner.configure_logging")
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
