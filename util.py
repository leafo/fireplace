
import gtk

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}

def html_escape(text):
     return "".join(html_escape_table.get(c,c) for c in text)

class HasController(object):
    @property
    def me(self):
        return self.controller.me

    @property
    def network(self):
        return self.controller.network

    @property
    def config(self):
        return self.controller.config

