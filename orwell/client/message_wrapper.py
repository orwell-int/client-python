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
