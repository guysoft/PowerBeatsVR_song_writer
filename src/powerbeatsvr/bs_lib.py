import json
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
    }
}


def get_data(bs_info_path):
    data = None
    with open(bs_info_path) as f:
        data = json.load(f)
    return {
        "bpm": int(data["_beatsPerMinute"]),
        "offset": float(data["_songTimeOffset"]),
        "name": data["_songName"],
        "author": data["_songAuthorName"]
        }

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
