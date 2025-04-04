import time

class Room:
  __players: list[str]
  __players_active: dict[str, bool]
  
  __hostSid: str
  
  __walls: list
  __game_started: bool
  __created_at: float
  
  def __init__(self, walls, host_sid):
    self.__players = [host_sid]
    self.__players_active = {host_sid: True}    
    
    self.__hostSid = host_sid
    
    self.__walls = walls
    self.__game_started = False
    self.__created_at = time.time()
  
  def get_walls(self):
    return self.__walls
  
  def get_players(self):
    return self.__players
  
  def add_player(self, sid: str):
    self.__players.append(sid)
    self.__players_active[sid] = True

  def remove_player(self, sid: str):
    if sid not in self.__players_active:
      return
    
    self.__players.remove(sid)
    del self.__players_active[sid]
    
    # If the player is the host, remove the room
    if sid == self.__hostSid:
      self.__hostSid = None
      for player_sid in self.__players:
        if self.__players_active[player_sid]:
          self.__hostSid = player_sid
          break
        
  def is_player_in_room(self, sid: str):
    return sid in self.__players_active
  
  def get_player_position_index(self, sid: str):
    if sid not in self.__players:
      return None
    return self.__players.index(sid)
      
  def activate_player(self, sid: str):
    if sid not in self.__players:
      return
    self.__players_active[sid] = True

  def deactivate_player(self, sid: str):
    if sid not in self.__players:
      return
    self.__players_active[sid] = False

  def is_player_active(self, sid: str):
    return sid in self.__players_active and self.__players_active[sid]
  
  def get_num_players(self):  
    return len(self.__players)
  
  def get_num_active_players(self):
    return len([sid for sid in self.__players if self.__players_active[sid]])
  
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