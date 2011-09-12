import httplib
import base64
import urllib2
import json
import re

class Campfire(object):
    key = "eda1e05163b1bac206c701624480b8adaacc3fe6"
    url = "https://leafonet.campfirenow.com:443/"

    @classmethod
    def url_for_subdomain(self, domain):
        return "https://%s.campfirenow.com:443/" % domain

    def __init__(self, key=None, url=None):
        self.rooms = None
        if key is not None: self.key = key
        if url is not None: self.url = url

    def login(self, username, password):
        return self.api("users/me", auth=(username, password))

    def make_request(self, url, data=None, auth=None):
        print "Requesting:", url, "data:", data
        req = urllib2.Request(url, data=data)

        if auth is None: auth = (self.key, 'x')

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
        self.api("room/%d/join" % room['id'], "")
        return Room(self, room)

    def get_all_rooms(self):
        rooms = self.api("rooms")["rooms"]
        self.rooms = {}
        for room in rooms:
            self.rooms[room["name"]] = room

        return rooms

    def get_room_by_name(self, name, force=False):
        if self.rooms is None or force == True:
            self.get_all_rooms()

        return self.rooms[name]

class Room(object):
    def __init__(self, campfire, room):
        self.campfire = campfire
        self.room = room
        self.in_room = True
        self.detailed = None

    @property
    def id(self):
        return self.room['id']

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
                continue
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
    c = Campfire()

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
