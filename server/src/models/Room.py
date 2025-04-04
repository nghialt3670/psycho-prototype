import time
from models.Player import Player


class Room:
  __players: list[str]
  __hostSid: str
  
  __walls: list
  __game_started: bool
  __created_at: float
  
  def __init__(self, walls, host):
    self.__players = []
    self.__hostSid = host
    
    self.__walls = walls
    self.__game_started = False
    self.__created_at = time.time()
  
  def get_walls(self):
    return self.__walls
  
  def get_players(self):
    return self.__players
  
  def add_player(self, sid: str):
    self.__players.append(sid)
    
  def remove_player(self, sid: str):
    self.__players.remove(sid)
    if sid in self.__players and sid == self.__hostSid:
      self.__hostSid = self.__players[0] if self.__players else None
    
  def get_num_players(self):  
    return len(self.__players)
  
  def is_empty(self):
    return len(self.__players) == 0
    
  def get_hostSid(self):
    return self.__hostSid  
  
  def start_game(self):
    self.__game_started = True
    
  def is_game_started(self):
    return self.__game_started
  
  def get_creation_time(self):
    return self.__created_at