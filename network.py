
import gobject
gobject.threads_init()

import threading
import campfire
from campfire import Campfire

class AsyncProxy(object):
    _auto_proxy = set(['campfire'])

    def __init__(self, obj):
        self._obj = obj

    def _queue_result(self, callback, response):
        # see if we need to wrap the result...
        if response.__class__.__module__ in self._auto_proxy:
            print "wrapping result"
            response = AsyncProxy(response)
        gobject.idle_add(callback, response)

    def __str__(self):
        return "<AsyncProxy(%s)>" % str(self._obj)

    def __getattr__(self, name):
        func = getattr(self._obj, name)
        if not callable(func):
            return func

        def async_call(callback, *args, **kwargs):
            prox = self
            class CallbackThread(threading.Thread):
                def run(self):
                    try:
                        response = func(*args)
                        if callable(callback):
                            prox._queue_result(callback, response)
                    except Exception, e:
                        if "fail" not in kwargs: raise
                        prox._queue_result(kwargs["fail"], e)

            CallbackThread().start()

        return async_call

# wraps the root campfire object
class Network(AsyncProxy):
    def __init__(self, *args, **kwargs):
        self.campfire = Campfire(*args, **kwargs)
        super(Network, self).__init__(self.campfire)

class StreamingRoom(threading.Thread):
    def __init__(self, room, callback):
        super(StreamingRoom, self).__init__()
        self.daemon = True
        self.callback = callback
        self.room = room
        self.finished = False

    def queue_finish(self):
        self.finished = True

    def run(self):
        stream = self.room._obj.get_streaming()
        while True:
            if self.finished: return
            message = stream.get_message()
            if message is not None:
                self.callback(message)

