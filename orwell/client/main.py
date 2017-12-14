import zmq

import orwell.messages.controller_pb2 as pb_controller
import orwell.messages.server_game_pb2 as pb_server_game
from .broadcast import Broadcast



class Toto(object):

    def __init__(self):
        broadcast = Broadcast()
        print(broadcast.push_address + " / " + broadcast.subscribe_address)
        self._push_address = broadcast.push_address
        self._subscribe_address = broadcast.subscribe_address
        self._context = zmq.Context.instance()
        push_socket = self._context.socket(zmq.PUSH)
        push_socket.connect(self._push_address)
        self._push_stream = ZMQStream(push_socket)
        subscribe_socket = self._context.socket(zmq.SUB)
        subscribe_socket.connect(self._subscribe_address)
        subscribe_socket.setsockopt(zmq.SUBSCRIBE, "")

    def start(self):
        hello = self._build_hello(False)
        self._push_stream.send(hello)
        message = self._zmq_req_socket.recv()

    def _build_hello(self, ready):
        pb_message = pb_controller.Hello()
        name = "JAMBON"
        pb_message.name = name
        pb_message.ready = ready
        payload = pb_message.SerializeToString()
        return self._routing_id + ' Hello ' + payload


def main():
    pass
