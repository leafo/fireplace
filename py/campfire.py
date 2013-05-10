import httplib
import base64
import urllib2
import json
import re

class Campfire(object):
    @property
    def auth(self):
        if self.key is None:
            raise ValueError("client has no key")
        return (self.key, 'x')

    @classmethod
    def url_for_subdomain(self, domain):
        return "https://%s.campfirenow.com:443/" % domain

    def __init__(self, url, key=None):
        self.room_for_name = None
        self.room_for_id = None
        self.url = url
        self.key = key if key is not None else None

    def login(self, username, password):
        return self.api("users/me", auth=(username, password))

    def make_request(self, url, data=None, auth=None):
        print "Requesting:", url, "data:", data
        req = urllib2.Request(url, data=data)

        if auth is None: auth = self.auth

        auth = base64.encodestring('%s:%s' % auth)[:-1]
        req.add_header("Authorization", "Basic " + auth)
        req.add_header("Content-Type", 'application/json')
        return req

    def api(self, path, post=None, ext=".json", auth=None):
        url = self.url + path + ext
        req = self.make_request(url, post, auth=auth)

        u = urllib2.urlopen(req)
        try:
            return json.loads(u.read())
        except ValueError:
            return {}

    def join(self, room_name):
        room = self.get_room_by_name(room_name)
        if room is None: raise ValueError("unknown room %s" % room_name)
        self._join_by_id(room["id"])
        return Room(self, room)

    def join_by_id(self, room_id):
        room = self.get_room_by_id(room_id)
        if room is None: raise ValueError("unknown room %s" % room_id)
        self._join_by_id(room_id)
        print room
        return Room(self, room)

    def _join_by_id(self, room_id):
        self.api("room/%d/join" % room_id, "")

    def get_all_rooms(self):
        rooms = self.api("rooms")["rooms"]
        self.room_for_name = {}
        self.room_for_id = {}
        for room in rooms:
            self.room_for_name[room["name"]] = room
            self.room_for_id[room["id"]] = room

        return rooms

    def get_room_by_name(self, name, force=False):
        if self.room_for_name is None or force == True:
            self.get_all_rooms()

        return self.room_for_name[name]

    def get_room_by_id(self, id, force=False):
        if self.room_for_id is None or force == True:
            self.get_all_rooms()

        return self.room_for_id[id]

class Room(object):
    def __init__(self, campfire, room):
        self.campfire = campfire
        self.room = room
        self.in_room = True
        self.detailed = None

    @property
    def id(self):
        return self.room['id']

    @property
    def name(self):
        return self.room['name']

    @property
    def topic(self):
        return self.room['topic']

    def get_users(self):
        if self.detailed is None:
            self.detailed = self.campfire.api("room/%d" % self.id)

        return self.detailed["room"]["users"]

    def speak(self, text):
        if not self.in_room: raise ValueError("not in room")
        req = json.dumps({"message": { "type": "TextMessage", "body": text}})
        self.campfire.api("room/%d/speak" % self.id, req)

    def leave(self): # leave this room
        self.campfire.api("room/%d/leave" % self.id, "")

    def get_streaming(self):
        return StreamingRoom(self)

class StreamingRoom(Campfire):
    url = "https://streaming.campfirenow.com:443/"

    def __init__(self, room):
        self.conn = None
        self.room = room

    def get_message(self):
        if self.conn is None:
            print "setting up connection"
            req = self.campfire.make_request(self.url + "room/%d/live.json" % self.room.id)
            self.conn = urllib2.urlopen(req)

        # we get a newline every second or something for some reason?
        buff = []
        while True:
            c = self.conn.read(1)
            if c.isspace():
                return None
            else:
                buff.append(c)
                while True:
                    c = self.conn.read(1)
                    if c == "\r":
                        return json.loads("".join(buff))
                    buff.append(c)

    @property
    def campfire(self):
        return self.room.campfire

if __name__ == "__main__":
    c = Campfire(Campfire.url_for_subdomain("leafonet"))

    print c.login("leafot@gmail.com", "brokepass")

    # r = c.join("Room 1")
    # r.speak("what is goin: on here")
    # stream = r.get_streaming()
    # try:
    #     while True:
    #         print stream.get_message()
    # except KeyboardInterrupt:
    #     r.leave()

    # # r.leave()
    # print c.api("presence")
