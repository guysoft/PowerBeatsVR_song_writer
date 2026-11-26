import json
import os
# Map Format Doc
# https://bsmg.wiki/mapping/map-format.html

#def get_bpm(bs_info_path):
    #data = None
    #with open(bs_info_path) as f:
        #data = json.load(f)
    #return int(data["_beatsPerMinute"])
    
NOTE_TYPE = {"BOMB": 3}
OBSTACLE_TYPE = {"FULL_HEIGHT": 0,
                 "CROUCH": 1}

VERSION_KEYS = {
    2:
    {
        "_time": "_time",
        "_lineIndex": "_lineIndex",
        "_lineLayer": "_lineLayer",
        "_duration": "_duration",
        "_width": "_width",
        "_height": None,
    },
    3:
    {
        "_time": "b",
        "_lineIndex": "x",
        "_lineLayer": "y",
        "_duration": "d",
        "_width": "w",
        "_height": "h",
    },
    # v4 uses the same short keys as v3, but "b" is in beats instead of
    # seconds and the objects live in separate "*Data" arrays.
    4:
    {
        "_time": "b",
        "_lineIndex": "x",
        "_lineLayer": "y",
        "_duration": "d",
        "_width": "w",
        "_height": "h",
    }
}


def get_info(bs_info_path):
    with open(bs_info_path) as f:
        return json.load(f)


def is_v4_info(info_data):
    version = info_data.get("version") or info_data.get("_version") or ""
    return str(version).startswith("4.")


def get_data_from_info(data):
    if is_v4_info(data):
        # v4 drops the leading underscores and splits song/audio metadata
        song = data.get("song") or {}
        audio = data.get("audio") or {}
        return {
            "bpm": float(audio.get("bpm") or 0),
            "offset": float(audio.get("songTimeOffset") or 0),
            "name": song.get("title", "unknown"),
            "author": song.get("author", "unknown"),
        }
    return {
        "bpm": int(data["_beatsPerMinute"]),
        "offset": float(data["_songTimeOffset"]),
        "name": data["_songName"],
        "author": data["_songAuthorName"]
        }


def get_data(bs_info_path):
    return get_data_from_info(get_info(bs_info_path))


def get_difficulty_files(info_data):
    """
    v4 only: map difficulty name to the file holding it, e.g.
    {"ExpertPlus": "ExpertPlus.beatmap.dat"}. In v4 the file names are only
    known from Info.dat, "<Difficulty>.dat" no longer exists.
    """
    result = {}
    for beatmap in info_data.get("difficultyBeatmaps") or []:
        characteristic = beatmap.get("characteristic", "Standard")
        difficulty = beatmap.get("difficulty")
        filename = beatmap.get("beatmapDataFilename")
        if characteristic == "Standard" and difficulty and filename:
            result[difficulty] = filename
    return result


def get_bpm_segments(folder, info_data):
    """
    Read AudioData.dat (v4) and return [(start_beat, end_beat,
    start_seconds, end_seconds), ...] so beats can be converted to seconds
    even when the song changes tempo. Returns [] when there is no such data.
    """
    audio = info_data.get("audio") or {}
    filename = audio.get("audioDataFilename")
    if not filename:
        return []
    path = os.path.join(folder, filename)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        audio_data = json.load(f)
    frequency = audio_data.get("songFrequency") or 44100
    segments = []
    for segment in audio_data.get("bpmData") or []:
        start_beat = segment.get("sb")
        end_beat = segment.get("eb")
        start_sample = segment.get("si")
        end_sample = segment.get("ei")
        if None in (start_beat, end_beat, start_sample, end_sample):
            continue
        if end_beat <= start_beat:
            continue
        segments.append((start_beat, end_beat,
                         start_sample / frequency, end_sample / frequency))
    return segments


def beats_to_seconds(beat, segments=None, bpm=0):
    """
    v4 timings are in beats, everything downstream expects seconds.
    Falls back to a constant BPM when there is no bpmData (or for beats
    outside the known segments).
    """
    if segments:
        for start_beat, end_beat, start_seconds, end_seconds in segments:
            if start_beat <= beat <= end_beat:
                return start_seconds + (beat - start_beat) * (
                    end_seconds - start_seconds) / (end_beat - start_beat)
        nearest = segments[0] if beat < segments[0][0] else segments[-1]
        start_beat, end_beat, start_seconds, end_seconds = nearest
        return start_seconds + (beat - start_beat) * (
            end_seconds - start_seconds) / (end_beat - start_beat)
    if not bpm:
        raise ValueError("map has no BPM, cannot convert beats to seconds")
    return beat * 60.0 / bpm

# The width from each side in the center (the total width is twice this number)
LEVEL_WITH = 1.1
# Lowest point in the game map beneeth your center
LEVEL_LOW = -0.5
# Highest point in the map
LEVEL_HIGH = 1.0
def line_index_layer_to_position(note_x, note_y):
    # beat saber layer moves between 0-2
    # beat saber index moves between 0-3
    # max posy in beat saber = 0.5 - 1.0
    # max posx in beat saber = -1.3 - 1.3
    position_x = -LEVEL_WITH + (2*LEVEL_WITH/3) *note_x
    position_y = LEVEL_LOW + (LEVEL_HIGH - LEVEL_LOW)/2 * note_y
    return [position_x, position_y]


def obstacle_line_index_layer_to_position(obstacle):
    # index 0 to 3
    # width 0-4 (can be negative but it creates bugs in beat saber)
    # posy = 0.5 - 1.3
    # posx = -1.3 - 1.3
    
    # Left example
    # position = [-0.976259469985962,-1.29999995231628]
    PADDING = 2
    WALL_WIDTH = 0.5
    position_x = (-LEVEL_WITH  + (2*LEVEL_WITH/3) * obstacle["_lineIndex"]) * PADDING - WALL_WIDTH
    
    # 0.65 because the minimal size of -1.3 + 0.65 * 4 = 1.3
    # position_x2/position_y = position_x + 0.65 * obstacle["_width"]
    position_y = -0.976259469985962
    return [position_x, position_y]

def get_map_data(bs_map_path):
    data = None
    with open(bs_map_path) as f:
        data = json.load(f)
    
    current_beat = None
        
    return data
