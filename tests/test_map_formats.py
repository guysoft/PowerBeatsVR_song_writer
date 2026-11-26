"""
Format coverage tests for the Beat Saber -> PowerBeatsVR converter.

They build tiny synthetic maps for every supported map format and check the
converted output, so a map-format change cannot silently break the formats
that already worked. No real songs are needed (the audio file is a stub,
the converter only copies it).

Run with pytest, or directly: python3 tests/test_map_formats.py
"""
import json
import os
import shutil
import tempfile
import zipfile

from powerbeatsvr.writer import convert_beat_saber_zip


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def make_zip(files, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content if isinstance(content, bytes) else json.dumps(content))
    return zip_path


def convert(files):
    """Zip the given virtual files, convert them, return the output json."""
    workdir = tempfile.mkdtemp()
    try:
        zip_path = make_zip(files, os.path.join(workdir, "map.zip"))
        out_dir = os.path.join(workdir, "out")
        convert_beat_saber_zip(zip_path, out_dir)
        outputs = [name for name in os.listdir(out_dir) if name.endswith(".json")]
        assert outputs, "no converted json was produced"
        with open(os.path.join(out_dir, outputs[0])) as f:
            return json.load(f)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def beat_numbers(data, difficulty="Expert"):
    return [beat["beatNo"] for beat in data[difficulty]["beats"]]


def actions(data, difficulty="Expert"):
    found = []
    for beat in data[difficulty]["beats"]:
        found.extend(beat["actions"])
        for sub_beat in beat["subBeats"]:
            found.extend(sub_beat["actions"])
    return found


def v2_map(note_time=2.0):
    info = {
        "_version": "2.0.0",
        "_songName": "V2 Test",
        "_songAuthorName": "Tester",
        "_beatsPerMinute": 120,
        "_songTimeOffset": 0,
        "_songFilename": "song.egg",
    }
    difficulty = {
        "_version": "2.0.0",
        "_notes": [{"_time": note_time, "_lineIndex": 1, "_lineLayer": 0, "_type": 0, "_cutDirection": 1}],
        "_obstacles": [],
    }
    return {"Info.dat": info, "Expert.dat": difficulty, "song.egg": b"stub-audio"}


def v3_map(note_time=2.0):
    info = {
        "_version": "2.1.0",
        "_songName": "V3 Test",
        "_songAuthorName": "Tester",
        "_beatsPerMinute": 120,
        "_songTimeOffset": 0,
        "_songFilename": "song.egg",
    }
    difficulty = {
        "version": "3.3.0",
        "colorNotes": [{"b": note_time, "x": 1, "y": 0, "c": 0, "d": 1, "a": 0}],
        "bombNotes": [],
        "obstacles": [],
    }
    return {"Info.dat": info, "ExpertStandard.dat": difficulty, "song.egg": b"stub-audio"}


def v4_map(note_beat=4, folder=None, audio_data=None):
    info = {
        "version": "4.0.1",
        "song": {"title": "V4 Test", "author": "Tester"},
        "audio": {"songFilename": "song.egg", "bpm": 120.0},
        "difficultyBeatmaps": [{
            "characteristic": "Standard",
            "difficulty": "ExpertPlus",
            "beatmapDataFilename": "ExpertPlus.beatmap.dat",
        }],
    }
    if audio_data is not None:
        info["audio"]["audioDataFilename"] = "AudioData.dat"
    beatmap = {
        "version": "4.1.0",
        "colorNotes": [{"b": note_beat, "r": 0, "i": 0}],
        "colorNotesData": [{"x": 1, "y": 0, "c": 0, "d": 1, "a": 0}],
        "bombNotes": [{"b": note_beat, "r": 0, "i": 0}],
        "bombNotesData": [{"x": 2, "y": 0}],
        "obstacles": [{"b": 0, "r": 0, "i": 0}],
        "obstaclesData": [{"x": 0, "y": 0, "d": 4, "w": 1, "h": 5}],
    }
    files = {"Info.dat": info, "ExpertPlus.beatmap.dat": beatmap, "song.egg": b"stub-audio"}
    if audio_data is not None:
        files["AudioData.dat"] = audio_data
    if folder:
        files = {f"{folder}/{name}": content for name, content in files.items()}
    return files


def test_v2_map_converts():
    data = convert(v2_map(note_time=2.0))
    assert data["name"] == "V2 Test"
    assert 2 in beat_numbers(data)


def test_v3_map_converts():
    data = convert(v3_map(note_time=2.0))
    assert data["name"] == "V3 Test"
    assert 2 in beat_numbers(data)


def test_v4_map_reads_info_and_indirection():
    data = convert(v4_map(note_beat=4))
    assert data["name"] == "V4 Test"
    assert data["bpm"] == 120.0
    # 4 beats at 120bpm is 2 seconds
    assert 2 in beat_numbers(data)
    note_actions = actions(data)
    assert any(action["action"] == "NormalBall" for action in note_actions)
    assert any(action["action"] == "BallObstacle" for action in note_actions)
    assert any(action["action"] == "WallObstacle" for action in note_actions)


def test_v4_folder_wrapped_map_converts():
    data = convert(v4_map(note_beat=4, folder="a1b2c3"))
    assert data["name"] == "V4 Test"
    assert 2 in beat_numbers(data)


def test_v4_tempo_change_uses_beat_data():
    # 120 bpm for the first 120 beats (60s), then twice as fast: beats
    # 120-180 take 15s. A note on beat 150 is 30 beats into the fast part,
    # so it lands at 60 + 7.5 = 67.5s.
    audio_data = {
        "version": "4.0.0",
        "songFrequency": 44100,
        "bpmData": [
            {"si": 0, "ei": 44100 * 60, "sb": 0, "eb": 120},
            {"si": 44100 * 60, "ei": 44100 * 75, "sb": 120, "eb": 180},
        ],
    }
    data = convert(v4_map(note_beat=150, audio_data=audio_data))
    assert 67 in beat_numbers(data)


def test_v4_unsupported_version_still_errors():
    files = v4_map(note_beat=4)
    files["ExpertPlus.beatmap.dat"]["version"] = "5.0.0"
    try:
        convert(files)
    except Exception as error:
        assert "unknown map version" in str(error)
    else:
        raise AssertionError("expected an unknown map version error")


if __name__ == "__main__":
    import sys
    import traceback

    failures = 0
    for name in sorted(list(globals())):
        if not name.startswith("test_"):
            continue
        test = globals()[name]
        try:
            test()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
