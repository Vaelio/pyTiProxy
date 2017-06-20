from logging import INFO, basicConfig
from json import dumps


class StructuredMessage(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __str__(self):
        return '%s' % (dumps(self.kwargs))

_ = StructuredMessage  # for readability


def init_log():
    basicConfig(level=INFO, format='%(message)s')
    return _