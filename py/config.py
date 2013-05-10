
import gtk

import re
import json

import os
from os import path

class ConfigBase(object):
    def wrap_result(self, value, name, using_default):
        t = type(value)
        if t == dict:
            if using_default:
                value = {}
                self.set(name, value)
            return Config(value, self.defaults.get(name))
        if t == list:
            if using_default:
                value = []
                self.set(name, value)
            return ConfigArray(value, self.defaults.get(name))
        else:
            return value

class Config(ConfigBase):
    version = 1 # for migration
    default_name = ".fireplace"

    settings = None
    defaults = {
        "window_title": "Fireplace",
        "status_icon": True,
        "show_notifications": True,
        "server": { }
    }

    def __init__(self, settings, defaults=None):
        self.settings = settings
        if defaults is not None:
            self.defaults = defaults

    def save(self):
        with open(self.config_file_path(), "w") as f:
            f.write(json.dumps(self.settings))

    def get(self, name, default=None):
        using_default = False
        if name not in self.settings:
            using_default = True
            value = self.defaults.get(name, default)
        else:
            value = self.settings[name]

        return self.wrap_result(value, name, using_default)

    def follow_path(self, path):
        cfg = self
        for path_item in path:
            cfg = cfg.get(path_item, {})
        return cfg

    def set(self, name, value):
        self.settings[name] = value

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        try:
            object.__getattribute__(self, name)
            object.__setattr__(self, name, value)
        except AttributeError:
            self.set(name, value)

    def __contains__(self, name):
        return name in self.settings

    @classmethod
    def config_file_path(cls):
        home = os.getenv('USERPROFILE') or os.getenv('HOME')
        return path.join(home, cls.default_name)

    @classmethod
    def load_or_create(cls):
        try:
            with open(cls.config_file_path()) as f:
                settings = json.loads(f.read())
        except IOError:
            settings = { "version": cls.version }

        return cls(settings)

    def bind_to_widget(self, path, widget, validate=None):
        sync = ConfigSynchronizer(self)
        sync.associate(path, widget)
        sync.fill_widgets()
        sync.sync_on_change(widget)

class ConfigArray(ConfigBase):
    def __init__(self, items, defaults=None):
        self.items = items
        if defaults: self.defaults = defaults

    def get(self, index):
        using_default = False
        if index not in self.items:
            using_default = True
            value = self.defaults[index]
        else:
            value = self.items[index]

        return Config.wrap_result(value, index, using_default)

    def set(self, index, value):
        self.items[index] = value

class ConfigSynchronizer(object):
    def __init__(self, cfg):
        self.items = {} # path for widgets
        self.widget_for_path = {}
        self.cfg = cfg

    def serialize_value(self, widget):
        if isinstance(widget, gtk.Entry):
            return widget.get_text()

        if isinstance(widget, gtk.ToggleButton):
            return widget.get_active()

        if isinstance(widget, gtk.CheckMenuItem):
            return widget.get_active()

        raise TypeError("Unknown widget", widget)

    def update_widget_value(self, widget, value):
        if value is None: return
        if isinstance(widget, gtk.Entry):
            return widget.set_text(value)

        if isinstance(widget, gtk.ToggleButton):
            return widget.set_active(1 if value else 0)

        if isinstance(widget, gtk.CheckMenuItem):
            return widget.set_active(bool(value))

        raise TypeError("Unknown widget", widget)

    def sync_on_change(self, widget):
        def callback(*args): self.save_widget_values()

        if isinstance(widget, gtk.CheckMenuItem):
            widget.connect("toggled", callback)
            return

        raise TypeError("Unknown widget", widget)

    def get_subgroup(self, path):
        cfg = self.cfg
        for path_item in path[:-1]:
            cfg = cfg.get(path_item, {})
        return cfg

    # fill widgets with values from config
    def fill_widgets(self):
        for widget, path in self.items.items():
            cfg = self.cfg.follow_path(path[:-1])
            self.update_widget_value(widget, cfg.get(path[-1]))

    # copy widget values to config
    def save_widget_values(self):
        for widget, path in self.items.items():
            cfg = self.cfg.follow_path(path[:-1])
            cfg.set(path[-1], self.serialize_value(widget))
        self.cfg.save()

    def get_value(self, path):
        widget = self.widget_for_path[tuple(path.split("."))]
        return self.serialize_value(widget)

    def associate(self, path, widget, pre_save=None):
        path = path.split(".")
        self.items[widget] = path
        self.widget_for_path[tuple(path)] = widget

