#!/usr/bin/env python3
import json
import sys
import shutil
import os
import bs_lib
from bs_lib import NOTE_TYPE, line_index_layer_to_position

def ensure_dir(d, chmod=0o777):
    """
    Ensures a folder exists.
    Returns True if the folder already exists
    """
    if not os.path.exists(d):
        os.makedirs(d, chmod)
        os.chmod(d, chmod)
        return False
    return True

def create(name, author="unknown", bpm=140, offset=0):
    data = {
    "name": name,
    "author": author,
    "bpm": bpm,
    "offset": offset,
    "schemaVersion": 2,
    "Beginner": {
        "isGenerated": True,
        "beats": [],
        "maxHighscore" : 0
    },  
    "Advanced": {
                "isGenerated" : True,
        "maxHighscore" : 0,
        "beats": [],
            },
    "Expert": {
        "maxHighscore" : 0,
                "isGenerated" : True,
        "beats": []}
    }
    return data

"""
def add_beat(data, difficulty):
    beat = {
        "beatNo" : 4,
        "beatLabel" : "JUMP LEFT/RIGHT [4] Half: False Type: Spike Obstacle Rep: 0 Adv: 1 Gap: 1,1,0",
        "actions" : [
          {
            "position" : [-0.639522075653076,-1.29999995231628],
            "action" : "WallObstacle",
            "type" : 0,
            "depth" : 0.100000001490116
          },
          {
            "position" : [0.699999988079071,0.300000011920929],
            "action" : "BallObstacle"
          }
        ],
        "subBeats" : [
        ]
        }
    
    data[difficulty]["beats"].append(beat)
    return data
"""

def convert_action_type(note):
    if note["_type"] == NOTE_TYPE["BOMB"]:
        action = "BallObstacle"
    else:
        action = "NormalBall"
    return action

class Map():
    def __init__(self, name, author="unknown", bpm=140, offset=0):
        self.data = create(name, author=author, bpm=bpm, offset=offset)
    
    def add_beat(self, difficulty, beat_no, actions, sub_beats=[]):
        beat = {
            "beatNo": beat_no,
            "beatLabel" : "",
            "actions" : actions,
            "subBeats" : sub_beats
            }
        self.data[difficulty]["beats"].append(beat)
        return
        
        
    def get_powerbeatsvr_notes(self, bs_note_data, level):
        
        current_beat = None
        # TODO: Add subbeats - fraction beat numbers
        for note in bs_note_data["_notes"]:
            if note["_time"] % 1 == 0.0:
                if (current_beat is None or note["_time"] != current_beat):
                    if current_beat is not None:
                        self.add_beat(level, beat_no=int(current_beat), actions=actions, sub_beats=sub_beats)
                    current_beat = note["_time"]
                    # new beat
                    actions = []
                    sub_beats = []
                    
                actions.append({
                    "position" : line_index_layer_to_position(note),
                    "type": 0,
                    "depth": 0,
                    "action" : convert_action_type(note)})
                
            else:
                # Handle sub beats
                
                offset = note["_time"] - current_beat
                position = line_index_layer_to_position(note)
                    
                for i, subbeat_existing in enumerate(sub_beats):
                    if subbeat_existing["offset"] == offset:
                        sub_beats[i]["actions"].append(
                            {
                            "position" : position,
                            "action" : convert_action_type(note)
                            }
                            )
                else:
                    subbeat = {
                        "offset" : offset,
                        "actions" : [
                            {
                                "position" : position,
                                "action" : convert_action_type(note)
                            }
                            ]
                            }
                    
                    sub_beats.append(subbeat)
                    
                    
                 
                
                notes = []
                events = []
                obstacles = []
        # Add last beat
        self.add_beat(level, beat_no=int(current_beat), actions=actions, sub_beats=sub_beats)

        #actions = [
            #{
                #"position" : [-0.639522075653076,-1.29999995231628],
                #"action" : "WallObstacle",
                #"type" : 0,
                #"depth" : 0.100000001490116
            #},
            #{
                #"position" : [0.699999988079071,0.300000011920929],
                #"action" : "BallObstacle"
            #}
        #]
        return
        

def get_beat_number(a, number, difficulty):
    for i, beat in enumerate(a.data[difficulty]["beats"]):
        if beat[beatNo] == number:
            return i
    return None
    
if __name__ == "__main__":
    
    
    # bs_folder = "/home/guy/workspace/PowerBeatsVR/beatsaver_pack/Jaroslav Beck - Beat Saber (Built in)"
    bs_folder = sys.argv[1]
    out_folder = sys.argv[2]
    
    # Load BS data
    bs_info_path = os.path.join(bs_folder, 'Info.dat')
    bs_song_file = os.path.join(bs_folder, 'song.ogg')
    
    # out_folder = "/tmp/out"
    
    ensure_dir(out_folder)
    
    bs_map_easy_path = os.path.join(bs_folder, 'Easy.dat')
    bs_map_hard_path = os.path.join(bs_folder, 'Hard.dat')
    bs_map_expert_plus_path = os.path.join(bs_folder, 'ExpertPlus.dat')
    
    
    bs_data = bs_lib.get_data(bs_info_path)
    
    out_path = os.path.join(out_folder, bs_data["name"] + ".json")
    out_song_path = os.path.join(out_folder, bs_data["name"] + ".ogg")
    
    a = Map(name=bs_data["name"], author=bs_data["author"], bpm=bs_data["bpm"], offset=bs_data["offset"])
    
    levels_arrange = {bs_map_easy_path: "Beginner",
                      bs_map_hard_path: "Advanced",
                      bs_map_expert_plus_path: "Expert"}
    
    for key in levels_arrange.keys():
        bs_map_path = key
        difficulty = levels_arrange[key]
        bs_note_data = bs_lib.get_map_data(bs_map_path)
        a.get_powerbeatsvr_notes(bs_note_data, difficulty)
        
    # a.get_powerbeatsvr_notes(bs_note_data, "Expert")
    
    """
    # TODO ADD WALLS
    current_beat = None
    for obstacle in bs_note_data["_obstacles"]:
        if current_beat is None or note["_time"] != current_beat:
            if current_beat is not None:
                beat_index = get_beat_number(a, note["_time"], "Advanced")
                if beat_index is not None:
                    a["Advanced"]["beats"][beat_index]["actions"].append({"WallObstacle"})
                self.add_beat(level, beat_no=current_beat, actions=actions)
            current_beat = note["_time"]
        print(obstacle.keys())
    """
    
    # _notes', u'_events', u'', u'_obstacles
    
    with open(out_path,"w") as w:
        json.dump(a.data, w, indent=4, sort_keys=True)
    shutil.copy(bs_song_file, out_song_path)
