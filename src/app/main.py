#!/bin/bash
import os
from flask import Flask, render_template, request, send_from_directory
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
from powerbeatsvr.writer import ensure_dir, convert_beat_saber_zip
import tempfile

app = Flask(__name__)
Bootstrap(app)

SAVE_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
SHARE_FOLDER = os.path.join(os.path.dirname(__file__), "static", "downloads")

ensure_dir(SAVE_FOLDER)
ensure_dir(SHARE_FOLDER)

@app.route('/')
def upload_file():
   return render_template('upload.html')

@app.route('/download/<path:path>')
def send_js(path):
    return send_from_directory('static/downloads', path)
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file2():
   if request.method == 'POST':
      f = request.files['file']
      zip_path = os.path.join(SAVE_FOLDER, secure_filename(f.filename))
      f.save(zip_path)
      out_folder = tempfile.mkdtemp(dir=SHARE_FOLDER)
      print("out_folder: " + out_folder)
      folder_basename = os.path.basename(out_folder)
      ensure_dir(out_folder)
      song_name = convert_beat_saber_zip(zip_path, out_folder)
      
      song_url = "/download/" + folder_basename +"/" + song_name + ".ogg"
      json_url = "/download/" + folder_basename +"/" + song_name + ".json"
      print(song_url)
      return render_template('download_result.html', json_url=json_url, song_url=song_url)
		
if __name__ == '__main__':
   app.run(debug = True, port=80)
 
