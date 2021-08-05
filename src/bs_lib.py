import json
# Map Format Doc
# https://bsmg.wiki/mapping/map-format.html

#def get_bpm(bs_info_path):
    #data = None
    #with open(bs_info_path) as f:
        #data = json.load(f)
    #return int(data["_beatsPerMinute"])
    
NOTE_TYPE = {"BOMB": 3}


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
    # posy = 0.5 - 1.5
    # posx = -1.5 - 1.5
    position_x = -1.5  + 1 * note["_lineIndex"]
    position_y = -0.5  + 1 * note["_lineLayer"]
    return [position_x, position_y]

def get_map_data(bs_map_path):
    data = None
    with open(bs_map_path) as f:
        data = json.load(f)
    
    current_beat = None
        
    return data
