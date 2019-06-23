import abc


class Device(object):
    __metaclass__ = abc.ABCMeta

    # @abc.abstractmethod
    def process(self):
        pass

    @abc.abstractproperty
    def has_new_values(self):
        pass

    # @abs.abstractmethod
    def build_input(self):
        pass

    # @abs.abstractmethod
    def read_ping(self):
        pass
