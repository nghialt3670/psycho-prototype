from models.Vec2 import Vec2

class Player:
  sid: str
  position: Vec2
  username: str | None
  color: str | None
  room: str | None
  
  def __init__(self, sid: str, position: Vec2):
    self.sid = sid
    self.position = position
    self.username = None
    self.color = None
    self.room = None    