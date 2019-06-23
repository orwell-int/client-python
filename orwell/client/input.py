import orwell.messages.controller_pb2 as pb_controller


class Input(object):
    def __init__(
            self,
            left,
            right,
            fire_weapon1,
            fire_weapon2):
        pb_input = pb_controller.Input()
        pb_input.move.left = left
        pb_input.move.right = right
        pb_input.fire.weapon1 = fire_weapon1
        pb_input.fire.weapon2 = fire_weapon2
        self._payload = pb_input.SerializeToString()

    def get_message(self, routing_id):
        return routing_id + " Input " + self._payload
