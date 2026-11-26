#!/usr/bin/env python3
import json
import sys
import shutil
import os
from pyunpack import Archive
import tempfile
import powerbeatsvr.bs_lib as bs_lib
import glob
from powerbeatsvr.bs_lib import NOTE_TYPE, OBSTACLE_TYPE, VERSION_KEYS, line_index_layer_to_position, obstacle_line_index_layer_to_position, beats_to_seconds, get_bpm_segments, get_difficulty_files, get_info, is_v4_info

BS_LEVELS = ["Easy", "NormalStandard", "Normal", "HardStandard", "Hard", "Expert", "ExpertStandard", "ExpertPlusStandard", "ExpertPlus"]

# Lowest to highest, used to pick which difficulties to convert (v4)
DIFFICULTY_ORDER = ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"]


def sort_difficulties(names):
    def rank(name):
        return DIFFICULTY_ORDER.index(name) if name in DIFFICULTY_ORDER else len(DIFFICULTY_ORDER)
    return sorted(names, key=rank)

POWER_BEATS_VR_OBSTACLE_TYPES = {
    "FULL_HEIGHT": 0,
    "CROUCH": 7,
    "Double_Column": 1,
    "Archway Center": 2,
    "Archway Left": 3,
    "Archway Right": 4,
    "Opening Left": 5,
    "Opening Right": 6,
    }


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
    # In verson 2 there is a _type value for bombs and notes
    # In version 3 its two seprate lists
    if note["_type"] == NOTE_TYPE["BOMB"]:
        action = "BallObstacle"
    else:
        action = "NormalBall"
    return action

def merge_notes_and_bombs_v3(bs_note_data):
    return_value = []
    color_notes = []
    bombs = []
    for note in bs_note_data["colorNotes"]:
        note["_type"] = note["c"]
        color_notes.append(note)

    for bomb in bs_note_data["bombNotes"]:
        bomb["_type"] = NOTE_TYPE["BOMB"]
        bombs.append(bomb)

    return_value = color_notes + bombs
    return sorted(return_value, key=lambda d: d['b'])


def expand_notes_v4(bs_note_data, field, data_field, segments=None, bpm=0):
    """
    v4 keeps the timing in "colorNotes"/"bombNotes"/"obstacles" and the
    rest of each object (x/y/c/d/w/h) in a parallel "*Data" array, joined
    by the "i" index. Returns the merged objects with "b" in seconds.
    """
    data = bs_note_data.get(data_field) or []
    expanded = []
    for entry in bs_note_data.get(field) or []:
        index = entry.get("i")
        if index is None or index >= len(data):
            continue
        item = dict(data[index])
        item["b"] = beats_to_seconds(entry["b"], segments, bpm)
        expanded.append(item)
    return expanded


def merge_notes_and_bombs_v4(bs_note_data, segments=None, bpm=0):
    return_value = []
    for note in expand_notes_v4(bs_note_data, "colorNotes", "colorNotesData", segments, bpm):
        note["_type"] = note["c"]
        return_value.append(note)
    for bomb in expand_notes_v4(bs_note_data, "bombNotes", "bombNotesData", segments, bpm):
        bomb["_type"] = NOTE_TYPE["BOMB"]
        return_value.append(bomb)
    return sorted(return_value, key=lambda d: d['b'])


def get_obstacles_v4(bs_note_data, segments=None, bpm=0):
    data = bs_note_data.get("obstaclesData") or []
    obstacles = []
    for entry in bs_note_data.get("obstacles") or []:
        index = entry.get("i")
        if index is None or index >= len(data):
            continue
        obstacle = dict(data[index])
        start_beat = entry["b"]
        duration_beats = obstacle.get("d") or 0
        start_seconds = beats_to_seconds(start_beat, segments, bpm)
        end_seconds = beats_to_seconds(start_beat + duration_beats, segments, bpm)
        obstacle["b"] = start_seconds
        obstacle["d"] = end_seconds - start_seconds
        obstacles.append(obstacle)
    return obstacles


class Map():
    def __init__(self, name, author="unknown", bpm=140, offset=0, segments=None):
        self.data = create(name, author=author, bpm=bpm, offset=offset)
        self.bpm = bpm
        self.segments = segments or []
    
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

    def add_obstacle(self, difficulty, obstacle, version=2):
        current_time = obstacle[VERSION_KEYS[version]["_time"]]
        current_beat = int(current_time)
        
        # Handle intiger beat, goes in actions
        beat_index = self.get_beat(current_beat, difficulty)
            
        if beat_index is None:
            self.add_beat(difficulty, beat_no=current_beat, actions=[], sub_beats=[])
        beat_index = self.get_beat(current_beat, difficulty)
        
        
        # Get obstacle data
        x_position = obstacle[VERSION_KEYS[version]["_lineIndex"]]

        bs_type = None
        if version == 2:
            bs_type = obstacle["_type"]
        depth = obstacle[VERSION_KEYS[version]["_duration"]]
        width = obstacle[VERSION_KEYS[version]["_width"]]
        # y_position = x_position + width
        
        if depth == 0:
            return
        
        if version == 2:
            if bs_type == OBSTACLE_TYPE["CROUCH"]:
                
                if width < 4:
                    # This is a crouch wall, but its not going all the way to the end, so we are adding fall hight wall in the air to simulate
                    power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["FULL_HEIGHT"]
                    
                    # Take y from normal note location and x from obstacle position
                    # Dummy 0 for now
                    # TODO make this more pretty
                    obstacle["_lineLayer"] = 0
                    position = line_index_layer_to_position(obstacle["_lineIndex"], obstacle["_lineLayer"])
                    position[0], _ = obstacle_line_index_layer_to_position(obstacle)
                    
                else:
                    # Crouch wall with fall size
                    
                    power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["CROUCH"]
                    # print(current_time / 140)
                    
                    
                    # Taken from level editor, not sure if there are other ways to generate
                    # hard coded because anyway in beat saber its _lineIndex and width 4
                    position = [0, 0.472493290901184]
                
            elif bs_type == OBSTACLE_TYPE["FULL_HEIGHT"]:
                power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["FULL_HEIGHT"]
                
                position = obstacle_line_index_layer_to_position(obstacle)
            else:
                print("ERROR: Unknown wall type")
                exit(1)
            self.add_wall(current_time, position, difficulty, beat_index, power_beats_vr_type, depth, current_beat)

        elif version == 3:
            height = obstacle[VERSION_KEYS[version]["_height"]]
            y_position = obstacle[VERSION_KEYS[version]["_lineLayer"]]

            position = line_index_layer_to_position(x_position, y_position)

            if height == 1 and width > 2:
                power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["CROUCH"]

                self.add_wall(current_time, position, difficulty, beat_index, power_beats_vr_type, depth, current_beat)

            elif width == 1 and height > 2:
                power_beats_vr_type = POWER_BEATS_VR_OBSTACLE_TYPES["FULL_HEIGHT"]
                self.add_wall(current_time, position, difficulty, beat_index, power_beats_vr_type, depth, current_beat)

            else:
                print(f"Warning: Detected wall type that is not implemented width or height larger than 1 {[width, height]} location: {[x_position, y_position]}")


    def add_wall(self, current_time, position, difficulty, beat_index, power_beats_vr_type, depth, current_beat):
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

    def add_note(self, difficulty, note, version=2):
        current_time = note[VERSION_KEYS[version]["_time"]]
        current_beat = int(current_time)
        
        # Handle intager beat, goes in actions
        beat_index = self.get_beat(current_beat, difficulty)
            
        if beat_index is None:
            self.add_beat(difficulty, beat_no=current_beat, actions=[], sub_beats=[])
        beat_index = self.get_beat(current_beat, difficulty)
        
        
        # Get notes data
        x_position = note[VERSION_KEYS[version]["_lineIndex"]]

        action = convert_action_type(note)
        note_x = note[VERSION_KEYS[version]["_lineIndex"]]
        note_y = note[VERSION_KEYS[version]["_lineLayer"]]
        position = line_index_layer_to_position(note_x, note_y)
            
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


    def get_map_version(self, bs_note_data):
        version = bs_note_data.get("_version", None)
        if version is not None:
            return version
        version = bs_note_data.get("version", None)
        return version

    def get_powerbeatsvr_notes_v3(self, bs_note_data, level):
        notes_bombs = merge_notes_and_bombs_v3(bs_note_data)

        for note in notes_bombs:
            self.add_note(level, note, 3)
        return
        
    def get_powerbeatsvr_notes_v2(self, bs_note_data, level):
        for note in bs_note_data["_notes"]:
            self.add_note(level, note, 2)
        return

    def get_powerbeatsvr_obstacles_v3(self, bs_note_data, level):
        for obstacle in bs_note_data["obstacles"]:
            self.add_obstacle(level, obstacle, 3)
        return

    def get_powerbeatsvr_obstacles_v2(self, bs_obstacle_data, level):
        for obstacle in bs_obstacle_data["_obstacles"]:
            # print(obstacle)
            self.add_obstacle(level, obstacle, 2)


    def get_powerbeatsvr_notes_v4(self, bs_note_data, level):
        for note in merge_notes_and_bombs_v4(bs_note_data, self.segments, self.bpm):
            self.add_note(level, note, 3)
        return

    def get_powerbeatsvr_notes(self, bs_note_data, level):
        version = self.get_map_version(bs_note_data)
        if version is not None and version.startswith("2."):
            return self.get_powerbeatsvr_notes_v2(bs_note_data, level)
        elif version is not None and version.startswith("3."):
            return self.get_powerbeatsvr_notes_v3(bs_note_data, level)
        elif version is not None and version.startswith("4."):
            return self.get_powerbeatsvr_notes_v4(bs_note_data, level)
        else:
            raise Exception("unknown map version")
        return

    def get_powerbeatsvr_obstacles_v4(self, bs_note_data, level):
        for obstacle in get_obstacles_v4(bs_note_data, self.segments, self.bpm):
            self.add_obstacle(level, obstacle, 3)
        return

    def get_powerbeatsvr_obstacles(self, bs_note_data, level):
        version = self.get_map_version(bs_note_data)
        if version is not None and version.startswith("2."):
            return self.get_powerbeatsvr_obstacles_v2(bs_note_data, level)
        elif version is not None and version.startswith("3."):
            return self.get_powerbeatsvr_obstacles_v3(bs_note_data, level)
        elif version is not None and version.startswith("4."):
            return self.get_powerbeatsvr_obstacles_v4(bs_note_data, level)
        else:
            raise Exception("unknown map version")
        return
            
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
    bs_info_path = get_bs_info_path(bs_folder)
    bs_info = get_info(bs_info_path)
    is_v4 = is_v4_info(bs_info)
    # In v4 the difficulty file names are only known from Info.dat
    difficulty_files = get_difficulty_files(bs_info) if is_v4 else {}
    # v4 timings are in beats, convert them with the song tempo
    segments = get_bpm_segments(bs_folder, bs_info) if is_v4 else []

    def difficulty_path(name):
        return os.path.join(bs_folder, difficulty_files.get(name, name + ".dat"))

    bs_song_file = get_bs_song_path(bs_folder)

    # out_folder = "/tmp/out"

    ensure_dir(out_folder)

    bs_map_easy_path = difficulty_path(difficulty_list[0])
    bs_map_hard_path = difficulty_path(difficulty_list[1])
    bs_map_expert_path = difficulty_path(difficulty_list[2])


    bs_data = bs_lib.get_data_from_info(bs_info)

    out_path = os.path.join(out_folder, bs_data["name"] + ".json")
    out_song_path = os.path.join(out_folder, bs_data["name"] + ".ogg")

    a = Map(name=bs_data["name"], author=bs_data["author"], bpm=bs_data["bpm"], offset=bs_data["offset"], segments=segments)

    
    levels_arrange = {"Beginner": bs_map_easy_path,
                      "Advanced": bs_map_hard_path,
                      "Expert": bs_map_expert_path}
    
    for key in levels_arrange.keys():
        bs_map_path = levels_arrange[key]
        difficulty = key
        bs_note_data = bs_lib.get_map_data(bs_map_path)
        a.get_powerbeatsvr_notes(bs_note_data, difficulty)
        a.get_powerbeatsvr_obstacles(bs_note_data, difficulty)
    
    with open(out_path,"w") as w:
        json.dump(a.data, w, indent=4, sort_keys=True)
    shutil.copy(bs_song_file, out_song_path)
    return bs_data["name"]

def find_map_root(folder):
    """
    BeatSaver wraps the map files in a single top level folder
    ("<hash>/Info.dat"), while older zips are flat. Descend into the
    single sub folder until the level files are found.
    """
    root = folder
    for _ in range(3):
        names = os.listdir(root)
        has_info = any(name.lower() == "info.dat" for name in names)
        if has_info or any(os.path.splitext(name)[0] in BS_LEVELS for name in names):
            return root
        sub_dirs = [name for name in os.listdir(root)
                    if name != "__MACOSX" and os.path.isdir(os.path.join(root, name))]
        if len(sub_dirs) != 1:
            return root
        root = os.path.join(root, sub_dirs[0])
    return root


def get_available_levels(map_root):
    info_path = get_bs_info_path(map_root)
    info_data = get_info(info_path) if info_path else None
    if info_data is not None and is_v4_info(info_data):
        difficulty_files = get_difficulty_files(info_data)
        return sort_difficulties([name for name, filename in difficulty_files.items()
                                  if os.path.isfile(os.path.join(map_root, filename))])
    return [os.path.splitext(name)[0] for name in os.listdir(map_root)
            if os.path.splitext(name)[0] in BS_LEVELS]


def convert_beat_saber_zip(bs_zip, out_folder):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print("Temp folder: " + tmpdir)
        Archive(bs_zip).extractall(tmpdir)
        print(os.listdir(tmpdir))
        map_root = find_map_root(tmpdir)
        print("Map root: " + map_root)
        avilable_levels = get_available_levels(map_root)
                
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
            
        return_value = convert_beat_saber_folder(map_root, out_folder, difficulty_list)
    
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
