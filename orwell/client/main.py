import zmq

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.server_game_pb2 as pb_server_game
from .broadcast import Broadcast
import exceptions



class Toto(object):

    def __init__(self):
        broadcast = Broadcast()
        print(broadcast.push_address + " / " + broadcast.subscribe_address)
        self._push_address = broadcast.push_address
        self._subscribe_address = broadcast.subscribe_address
        self._context = zmq.Context.instance()
        self._push_socket = self._context.socket(zmq.PUSH)
        self._push_socket.connect(self._push_address)
        self._subscribe_socket = self._context.socket(zmq.SUB)
        self._subscribe_socket.connect(self._subscribe_address)
        self._subscribe_socket.setsockopt(zmq.SUBSCRIBE, "")
        self._routing_id = "temporary_id_" + str(RANDOM.randint(0, 32768))
        self._robot = None
        self._team = None
        self._abort = False

    def start(self):
        hello = self._build_hello(False)
        self._push_socket.send(hello)
        # this does not work as there could be other messages pending
        message = self._subscribe_socket.recv()
        self._decode_hello_reply(message)

    def _build_hello(self, ready):
        pb_message = pb_controller.Hello()
        name = "JAMBON"
        pb_message.name = name
        pb_message.ready = ready
        payload = pb_message.SerializeToString()
        return self._routing_id + ' Hello ' + payload

    def _decode_hello_reply(self, message):
        recipient, message_type, payload = message.split(' ', 3)
        if ("Welcome" == message_type):
            self._handle_welcome(payload)
        elif ("Goodbye" == message_type):
            self._handle_goodbye(payload)
        else:
            raise exceptions.NameError("Wrong message type: " + message_type)

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
            print("playing ? " + str(message.game_state.playing))
            print("time left: " + str(message.game_state.seconds))
            self._update_running(message.game_state.playing)
            for team in message.game_state.teams:
                print(team.name + " (" + str(team.num_players) +
                      ") -> " + str(team.score))

    def _handle_goodbye(self, payload):
        message = pb_server_game.Goodbye()
        message.ParseFromString(payload)
        print("Goodbye ...")
        self._abort = True

def main():
    pass
