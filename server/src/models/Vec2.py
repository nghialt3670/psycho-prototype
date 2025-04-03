
class Vec2:
  x: float
  y: float
  
  def __init__(self, x: float, y: float):
    self.x = x
    self.y = y
    
  def normalize(self):
    length = self.length()
    if length == 0:
      return Vec2(0, 0)
    return Vec2(self.x / length, self.y / length)
  
  def add(self, other: 'Vec2'):
    return Vec2(self.x + other.x, self.y + other.y)
  
  def distance(self, other: 'Vec2'):
    return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
  
  def length(self):
    return (self.x ** 2 + self.y ** 2) ** 0.5
  
  