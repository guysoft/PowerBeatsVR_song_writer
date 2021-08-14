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

def line_index_layer_to_position(note):
    # layer 0-2
    # ndex 0-3
    # posy = 0.5 - 1.3
    # posx = -1.3 - 1.3
    position_x = -1.3  + 0.8 * note["_lineIndex"]
    position_y = -0.5  + 0.8 * note["_lineLayer"]
    return [position_x, position_y]


def obstacle_line_index_layer_to_position(obstacle):
    # index 0 to 3
    # width 0-4 (can be negative but it creates bugs in beat saber)
    # posy = 0.5 - 1.3
    # posx = -1.3 - 1.3
    
    # Left example
    # position = [-0.976259469985962,-1.29999995231628]
    position_x = -1.3  + 0.8 * obstacle["_lineIndex"]
    
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
