
import gtk

import re
import json

import os
from os import path

class Config(object):
    version = 1 # for migration
    default_name = ".fireplace"

    settings = None
    defaults = {
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

        if type(value) == dict:
            if using_default:
                value = {}
                setattr(self, name, value)
            return Config(value, self.defaults.get(name))
        else:
            return value

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

        raise TypeError("Unknown widget", widget)

    def update_widget_value(self, widget, value):
        if value is None: return
        if isinstance(widget, gtk.Entry):
            return widget.set_text(value)

        if isinstance(widget, gtk.ToggleButton):
            return widget.set_active(1 if value else 0)

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

    def associate(self, path, widget):
        path = path.split(".")
        self.items[widget] = path
        self.widget_for_path[tuple(path)] = widget

