import json
import sys
path = '/home/guy/workspace/PowerBeatsVR/13 Abandon Ship.json'

data = None
with open(path) as f:
    data = json.load(f)
    

labels = []
min_pos_x = None
max_pos_x = None

min_pos_y = None
max_pos_y = None

for beat in data["Advanced"]["beats"]:
    if beat["beatLabel"] not in labels:
        labels.append(beat["beatLabel"])
        
    actions = beat["actions"]
    
    for action in actions:
    
        if "position" in action:
            if min_pos_x is None or action["position"][0] < min_pos_x:
                min_pos_x = action["position"][0]
            if max_pos_x is None or action["position"][0] > max_pos_x:
                max_pos_x = action["position"][0]
                
            if min_pos_y is None or action["position"][1] < min_pos_y:
                min_pos_y = action["position"][1]
            if max_pos_y is None or action["position"][1] > max_pos_y:
                max_pos_y = action["position"][1]

for i in labels:
    print(i)
print(max_pos_x)
print(min_pos_x)
print(max_pos_y)
print(min_pos_y)
