#!/usr/bin/env python3
import json
import sys
import shutil
import os
from pyunpack import Archive
import tempfile
import powerbeatsvr.bs_lib as bs_lib
import glob
from powerbeatsvr.bs_lib import NOTE_TYPE, OBSTACLE_TYPE, line_index_layer_to_position, obstacle_line_index_layer_to_position

BS_LEVELS = ["Easy", "NormalStandard", "Normal", "HardStandard", "Hard", "Expert", "ExpertStandard", "ExpertPlusStandard", "ExpertPlus"]

POWER_BEATS_VR_OBSTACLE_TYPES = {"FULL_HEIGHT": 0, "CROUCH": 7}


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
    
    def get_beat(self, number, difficulty):
        if number is None:
            return None
        for i, beat in enumerate(self.data[difficulty]["beats"]):
            if beat["beatNo"] == int(number):
                return i
        return None


    def get_sub_beat(self, difficulty, beat_index, offset):
        if beat_index is None:
            return None
        for i, sub_beat in enumerate(self.data[difficulty]["beats"][beat_index]["subBeats"]):
            if sub_beat["offset"] == offset:
                return i
        return None

    def add_obstacle(self, difficulty, obstacle):
        current_time = obstacle["_time"]
        current_beat = int(current_time)
        
        # Handle intiger beat, goes in actions
        beat_index = self.get_beat(current_beat, difficulty)
            
        if beat_index is None:
            self.add_beat(difficulty, beat_no=current_beat, actions=[], sub_beats=[])
        beat_index = self.get_beat(current_beat, difficulty)
        
        
        # Get obstacle data
        x_position = obstacle["_lineIndex"]
        bs_type = obstacle["_type"]
        depth = obstacle["_duration"]
        width = obstacle["_width"]
        # y_position = x_position + width
        
        if bs_type == OBSTACLE_TYPE["CROUCH"]:
            power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["CROUCH"]
            # Taken from level editor, not sure if there are other ways to generate
            # hard coded because anyway in beat saber its _lineIndex and width 4
            position = [0, 0.472493290901184]
        
        elif bs_type == OBSTACLE_TYPE["FULL_HEIGHT"]:
            power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["FULL_HEIGHT"]
            
            position = obstacle_line_index_layer_to_position(obstacle)
        else:
            print("ERROR: Unknown wall type")
            exit(1)
            
        if current_time % 1 == 0.0:
            self.data[difficulty]["beats"][beat_index]["actions"].append({
                "position" : position,
                "action" : "WallObstacle",
                "type" : power_beats_vr_type,
                "depth" : depth
                })
        else:
            offset = current_time - current_beat
            index_of_sub_beat = self.get_sub_beat(difficulty, beat_index, offset)
            if index_of_sub_beat is None:
                # Create new sub beat
                subbeat = {
                    "offset" : offset,
                    "actions" : []
                    }
                self.data[difficulty]["beats"][beat_index]["subBeats"].append(subbeat)
            index_of_sub_beat = self.get_sub_beat(difficulty, beat_index, offset)
                
            self.data[difficulty]["beats"][beat_index]["subBeats"][index_of_sub_beat]["actions"].append({
                "position" : position,
                "action" : "WallObstacle",
                "type" : power_beats_vr_type,
                "depth" : depth
                })

        return

    def add_note(self, difficulty, note):
        current_time = note["_time"]
        current_beat = int(current_time)
        
        # Handle intiger beat, goes in actions
        beat_index = self.get_beat(current_beat, difficulty)
            
        if beat_index is None:
            self.add_beat(difficulty, beat_no=current_beat, actions=[], sub_beats=[])
        beat_index = self.get_beat(current_beat, difficulty)
        
        
        # Get obstacle data
        x_position = note["_lineIndex"]
        bs_type = note["_type"]
        action = convert_action_type(note)
        position = line_index_layer_to_position(note)
            
        if current_time % 1 == 0.0:
            self.data[difficulty]["beats"][beat_index]["actions"].append({
                "position" : position,
                "action" : action
                })
        else:
            offset = current_time - current_beat
            index_of_sub_beat = self.get_sub_beat(difficulty, beat_index, offset)
            if index_of_sub_beat is None:
                # Create new sub beat
                subbeat = {
                    "offset" : offset,
                    "actions" : []
                    }
                self.data[difficulty]["beats"][beat_index]["subBeats"].append(subbeat)
            index_of_sub_beat = self.get_sub_beat(difficulty, beat_index, offset)
            
            self.data[difficulty]["beats"][beat_index]["subBeats"][index_of_sub_beat]["actions"].append({
                "position" : position,
                "action" : action
                })

        return                
        
    def get_powerbeatsvr_notes(self, bs_note_data, level):
        for note in bs_note_data["_notes"]:
            self.add_note(level, note)
        return
    
    def get_powerbeatsvr_obstacles(self, bs_obstacle_data, level):
        for obstacle in bs_obstacle_data["_obstacles"]:
            # print(obstacle)
            self.add_obstacle(level, obstacle)
            
def get_bs_info_path(folder):
    options = ["Info.dat", "info.dat"]
    for option in options:
        if os.path.isfile(os.path.join(folder, option)):
            return os.path.join(folder, option)
        
def get_bs_song_path(folder):
    for song_file in glob.glob(os.path.join(folder, "*.ogg")):
        return song_file
    for song_file in glob.glob(os.path.join(folder, "*.egg")):
        return song_file
    
def convert_beat_saber_folder(bs_folder, out_folder, difficulty_list=["Easy", "Hard", "ExpertPlus"]):
    # bs_folder = "/home/guy/workspace/PowerBeatsVR/beatsaver_pack/Jaroslav Beck - Beat Saber (Built in)"
    # Load BS data
    beginner = difficulty_list[0] + ".dat"
    advanced = difficulty_list[1] + ".dat"
    expert = difficulty_list[2] + ".dat"
    
    bs_info_path = get_bs_info_path(bs_folder)
    bs_song_file = get_bs_song_path(bs_folder)
    
    # out_folder = "/tmp/out"
    
    ensure_dir(out_folder)
    
    bs_map_easy_path = os.path.join(bs_folder, beginner)
    bs_map_hard_path = os.path.join(bs_folder, advanced)
    bs_map_expert_path = os.path.join(bs_folder, expert)
    
    
    bs_data = bs_lib.get_data(bs_info_path)
    
    out_path = os.path.join(out_folder, bs_data["name"] + ".json")
    out_song_path = os.path.join(out_folder, bs_data["name"] + ".ogg")
    
    a = Map(name=bs_data["name"], author=bs_data["author"], bpm=bs_data["bpm"], offset=bs_data["offset"])
    
    levels_arrange = {bs_map_easy_path: "Beginner",
                      bs_map_hard_path: "Advanced",
                      bs_map_expert_path: "Expert"}
    
    for key in levels_arrange.keys():
        bs_map_path = key
        difficulty = levels_arrange[key]
        bs_note_data = bs_lib.get_map_data(bs_map_path)
        a.get_powerbeatsvr_notes(bs_note_data, difficulty)
        a.get_powerbeatsvr_obstacles(bs_note_data, difficulty)
    
    with open(out_path,"w") as w:
        json.dump(a.data, w, indent=4, sort_keys=True)
    shutil.copy(bs_song_file, out_song_path)
    return bs_data["name"]

def convert_beat_saber_zip(bs_zip, out_folder):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print("Temp folder: " + tmpdir)
        Archive(bs_zip).extractall(tmpdir)
        print(os.listdir(tmpdir))
        avilable_levels = []
        for file_path in os.listdir(tmpdir):
            if file_path[:-4] in BS_LEVELS:
                avilable_levels.append(file_path[:-4])
                
        if len(avilable_levels) == 0:
            raise Exception("No levels found in package")
        
        if len(avilable_levels) == 1:
            difficulty_list = [avilable_levels[0], avilable_levels[0], avilable_levels[0]]
        elif len(avilable_levels) == 2:
            difficulty_list = [avilable_levels[0], avilable_levels[1], avilable_levels[1]]
        elif len(avilable_levels) == 3:
            difficulty_list = avilable_levels
        else:
            # More than 3
            difficulty_list = [avilable_levels[0], avilable_levels[1], avilable_levels[2]]
            
        return_value = convert_beat_saber_folder(tmpdir, out_folder, difficulty_list)
    
    return return_value

def run():
    import argparse
    parser = argparse.ArgumentParser(add_help=True,
                                     description="Convert beast saver custom map in to a powerbeastsvr one")

    parser.add_argument('convert_beat_saber_zip', type=str, help='zip file of a BeatSaber song map')
    parser.add_argument('output_folder', type=str, help='Folder to output the PowerBeatsVR json map and song file')
    # parser.add_argument('difficulty', type=str, help='Which level difficulty to use eg. Easty,Hard,ExpertPlus (default is exmaple)')
    args = parser.parse_args()
    
    
    convert_beat_saber_zip(args.convert_beat_saber_zip, args.output_folder)

if __name__ == "__main__":
    convert_beat_saber_folder(sys.argv[1], sys.argv[2], ["Easy", "Hard", "ExpertPlus"])
