while true do
  print "tick!"
  ngx.say("hello");
  ngx.flush(true)
  ngx.sleep(1)
end
