
import gtk
class HasController(object):
    @property
    def me(self):
        return self.controller.me

    @property
    def network(self):
        return self.controller.network

