from powerbeatsvr.writer import convert_beat_saber_folder
import sys

if __name__ == "__main__":
    convert_beat_saber_folder(sys.argv[1], sys.argv[2], ["Easy", "Hard", "ExpertPlus"])