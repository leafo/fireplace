require "moon"

lgi = require "lgi"
import Gdk, Gtk, GObject, Soup from lgi

json = require "cjson"

make_login = ->

  login_btn = Gtk.Button {
    label: "Login"
    on_clicked: =>
      print "Hello world"
  }

  buttons = Gtk.HButtonBox {
    login_btn
  }

  domain_entry = Gtk.Entry!
  username_entry = Gtk.Entry!
  password_entry = Gtk.Entry visibility: false

  make_row = (label, entry) ->
    align = Gtk.Alignment {
      xalign: 1
      xscale: 0
      Gtk.Label(:label)
    }

    align.width_request = 80
    with Gtk.HBox false, 8
      \pack_start align, false, false, 10
      \pack_start entry, true, true, 0

  box = with Gtk.VBox false, 4
    \pack_start make_row("Domain", domain_entry), true, true, 0
    \pack_start make_row("Username", username_entry), true, true, 0
    \pack_start make_row("Password", password_entry), true, true, 0
    \pack_start buttons, true, true, 0

  Gtk.Window {
    title: "Login"
    border_width: 8
    default_width: 320
    default_height: 200

    on_key_press_event: (e) =>
      if e.string\byte! == 27
        return Gtk.main_quit!

    box
  }




test_window = ->
  window = Gtk.Window {
    title: "This is my window"
    border_width: 8
    default_width: 320
    default_height: 200

    on_key_press_event: (e) =>
      if e.string\byte! == 27
        return Gtk.main_quit!

    on_show: (...) =>
      print "showing:", ...

    on_destroy: Gtk.main_quit
  }


store = Gtk.ListStore.new {
  GObject.Type.STRING
  GObject.Type.STRING
}

store\append { "Test", "Test" }
store\append { "AnotherTest", "HelloWorld" }

tree_view = Gtk.TreeView {
  model: store
  Gtk.TreeViewColumn {
    title: "First"
    {
      Gtk.CellRendererText {}
      { text: 1 }
    }
  }

  Gtk.TreeViewColumn {
    title: "Second"
    {
      Gtk.CellRendererText {}
      { text: 1 }
    }
  }
}

class Campfire
  new: (@domain) =>
    @url = "https://#{domain}.campfirenow.com/"

  list_rooms: =>
    url = @url .. "rooms.json"
    session = Soup.SessionAsync {
      on_authenticate: (s, msg, auth) ->
        auth\authenticate @user.api_auth_token, "x"
    }

    msg = Soup.Message.new "GET", url
    session\queue_message msg, (msg) =>
      print "Status:", msg.status_code
      print "Body:", msg.response_body.data

  login: (user, pass, callback) =>
    url = @url .. "users/me.json"

    session = Soup.SessionAsync {
      on_authenticate: (msg, auth) =>
        auth\authenticate user, pass
    }

    msg = Soup.Message.new "GET", url
    session\queue_message msg, (s, msg) ->
      error "failed to login" unless msg.status_code == 200
      @user = assert json.decode(msg.response_body.data).user
      moon.p @user
      callback @user if callback

-- window\add tree_view
text = Gtk.TextView!
scrolled = Gtk.ScrolledWindow { text }

fetch_btn = Gtk.Button {
  label: "Fetch"
  on_clicked: =>
    -- text.buffer.text = "Loading....."
    session = Soup.SessionAsync!
    msg = Soup.Message.new "GET", "http://localhost:8080"
    -- msg = Soup.Message.new "GET", "http://leafo.net"

    msg.on_got_chunk = (chunk) =>
      print "Chunk:", chunk.length
      print " data:", chunk.data
      print " get_data:", tostring(chunk\get_data!)
      print " get_as_bytes:", chunk\get_as_bytes!
      print!

      text.buffer.text ..= tostring chunk\get_data!


    session\queue_message msg, (msg) =>
      print msg.response_body
      text.buffer.text = msg.response_body.data

}

campfire = Campfire "leafonet"

-- login_btn = Gtk.Button {
--   label: "Log in"
--   on_clicked: =>
--     campfire\login "leafot@gmail.com", "thepassword", (user) =>
--       campfire\list_rooms!
-- }
-- 
-- buttons = Gtk.HButtonBox { fetch_btn, login_btn }
-- 
-- box = Gtk.VBox false
-- 
-- box\pack_start scrolled, true, true, 0
-- box\pack_start buttons, false, false, 8
-- 
-- window\add box
-- window\show_all!


w = make_login!
w\show_all!

Gtk.main!