
import gtk
from util import *
from config import ConfigSynchronizer

import urllib2

from campfire import Campfire
from network import Network

class Validator(object):
    def __init__(self):
        self.errors = []

    def not_empty(self, entry):
        text = entry.get_text()
        if not text:
            self.errors.append((entry, entry.label_text + " must not be empty"))
            return False
        return True

    def is_url(self, entry):
        text = entry.get_text()
        if not re.match(r"http(s?)://.", text):
            self.errors.append((entry, entry.label_text + " must be a url"))
            return False
        return True

class LoginDialog(gtk.Window):
    default_label_width = 80
    default_entry_width = 200

    def validate_input(self):
        v = Validator()
        v.not_empty(self.domain_entry)
        v.not_empty(self.user_entry)
        v.not_empty(self.pass_entry)
        return v.errors

    def entry_row(self, label_text, entry):
        hbox = gtk.HBox(False, 8)

        label = gtk.Label(label_text)
        label_align = gtk.Alignment(1.0, 0.5, 0,0)
        label_align.add(label)

        _w, h = label_align.size_request()
        label_align.set_size_request(self.default_label_width, h)

        _w, h = entry.size_request()
        entry.set_size_request(self.default_entry_width, h)


        hbox.pack_start(label_align, False)
        hbox.pack_start(entry, True, True)
        entry.connect("activate", self.on_activate)
        entry.label_text = label_text
        return hbox

    def _error(self, msg):
        md = gtk.MessageDialog(self,
                gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE, msg)
        md.run()
        md.destroy()

    def on_activate(self, btn):
        if not self.ready: return

        errors = self.validate_input()
        if errors:
            widget, msg = errors[0]
            self._error(msg)
            widget.grab_focus()
        else:
            url = Campfire.url_for_subdomain(self.sync.get_value("server.host"))
            print url
            self.network = Network(url=url)

            username = self.sync.get_value("server.username")
            password = self.sync.get_value("server.password")

            self.ready = False
            self.submit_button.set_sensitive(False)
            self.network.login(self.on_login, username, password, fail=self.on_fail_login)

    def on_login(self, me):
        self.sync.save_widget_values()
        self.controller.on_login(self.network, me["user"])

    def on_fail_login(self, err):
        self.submit_button.set_sensitive(True)
        if isinstance(err, urllib2.HTTPError):
            if err.code == 401:
                self._error("Failed to authenticate")
                self.user_entry.grab_focus()
            else:
                self._error(str(err))
        elif isinstance(err, urllib2.URLError):
            self._error("Failed to connect")
        else:
            raise err

    def __init__(self, controller):
        super(LoginDialog, self).__init__()
        self.controller = controller
        self.set_border_width(8)
        self.set_title("Connect to Campfire")

        self.domain_entry = gtk.Entry()
        self.user_entry = gtk.Entry()
        self.pass_entry = gtk.Entry()
        self.pass_entry.set_visibility(False)

        self.connect("delete_event", self.controller.on_delete)
        self.connect("destroy", self.controller.exit)

        self.ready = True

        vbox = gtk.VBox(False, 2)
        vbox.pack_start(self.entry_row("Domain", self.domain_entry), False)
        vbox.pack_start(self.entry_row("Username", self.user_entry), False)
        vbox.pack_start(self.entry_row("Password", self.pass_entry), False)

        button_row = gtk.HBox(False, 8)
        self.submit_button = gtk.Button("Login")
        self.submit_button.connect("clicked", self.on_activate)

        self.auto_check = gtk.CheckButton("Autoconnect")

        button_row.pack_start(self.auto_check)
        button_row.pack_start(self.submit_button)

        aligned_buttons = gtk.Alignment(1.0, 0.5, 0,0)
        aligned_buttons.add(button_row)

        vbox.pack_start(aligned_buttons, False)
        vbox.pack_start(gtk.HSeparator(), False, False, 5)

        self.session_picker = SessionList(self.controller)
        vbox.pack_start(self.session_picker, True, True)

        self.add(vbox)

        # attempt to load config
        self.sync = ConfigSynchronizer(controller.config)

        self.sync.associate("server.auto_connect", self.auto_check)
        self.sync.associate("server.host", self.domain_entry)
        self.sync.associate("server.username", self.user_entry)
        self.sync.associate("server.password", self.pass_entry)

        self.sync.fill_widgets()

        self.show_all()

class SessionList(gtk.VBox, HasController):
    def __init__(self, controller):
        super(SessionList, self).__init__(False, 4)
        sw = gtk.ScrolledWindow()

        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.store = gtk.ListStore(int, str, str, bool)
        tree_view = gtk.TreeView(self.store)
        tree_view.connect("row-activated", self.on_activate)
        tree_view.set_rules_hint(True)

        self.store.append([0, "hello", "world", True])

        self.create_columns(tree_view)
        sw.add(tree_view)

        button_row = gtk.HBox(False, 8)
        self.delete_button = gtk.Button("Delete")
        button_row.pack_start(self.delete_button)

        aligned_buttons = gtk.Alignment(1.0, 0.5, 0.0, 0.0)
        aligned_buttons.add(button_row)

        self.pack_start(sw, True, True)
        self.pack_start(aligned_buttons, False)

    def store_server(self, name, domain, password, auto):
        pass

    def find_for_name_domain(self, name, domain):
        pass

    def on_activate(self, tree, row, col):
        print "activated"

    def create_columns(self, tree_view):
        col = gtk.TreeViewColumn("", gtk.CellRendererToggle(), active=3)
        col.set_sort_column_id(3)
        tree_view.append_column(col)

        col = gtk.TreeViewColumn("Domain", gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        tree_view.append_column(col)

        col = gtk.TreeViewColumn("Username", gtk.CellRendererText(), text=2)
        col.set_sort_column_id(2)
        tree_view.append_column(col)



