from models.Vec2 import Vec2

class Player:
  sid: str
  position: Vec2
  username: str
  color: str
  room: str
  
  def __init__(self, sid: str, position: Vec2):
    self.sid = sid
    self.position = position
    self.username = None
    self.color = None
    self.room = None    