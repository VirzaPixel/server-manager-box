import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

## url
BASE_PUBLIC_URL = os.environ.get('BASE_PUBLIC_URL', '')

## folder
BASE_UPLOAD_FOLDER = os.environ.get('BASE_UPLOAD_FOLDER', 'alfal')

## category
categories_raw = os.environ.get('ALLOWED_CATEGORIES', '')
ALLOWED_CATEGORIES = [c.strip() for c in categories_raw.split(',') if c.strip()]

## max file length
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

if BASE_UPLOAD_FOLDER and not os.path.exists(BASE_UPLOAD_FOLDER):
    os.makedirs(BASE_UPLOAD_FOLDER)

for category in ALLOWED_CATEGORIES:
    category_path = os.path.join(BASE_UPLOAD_FOLDER, category)
    if not os.path.exists(category_path):
        os.makedirs(category_path)

## Read
@app.route('/files/<category>/<filename>', methods=['GET'])
def get_file(category, filename):
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori folder tidak valid'}), 400
    
    target_dir = os.path.join(BASE_UPLOAD_FOLDER, category)
    return send_from_directory(target_dir, filename)

## Create
@app.route('/upload/<category>', methods=['POST'])
def upload_file(category):
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori folder tidak valid !'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Name file kosong'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        target_dir = os.path.join(BASE_UPLOAD_FOLDER, category)

        # save file to folder
        file.save(os.path.join(target_dir, filename))

        url_publik = f"https://{BASE_PUBLIC_URL}/files/{category}/{filename}"

        return jsonify({
            'message': f"Upload ke {category} Berhasil !",
            'url' : url_publik
        }), 200
    
## Update
@app.route('/update/<category>/<filename>', methods=['PUT'])
def update_file(category, filename):
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori tidak Valid !'}), 400
    
    target_dir = os.path.join(BASE_UPLOAD_FOLDER, category)
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File tidak ditemukan !'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']

    os.remove(file_path)
    new_filename = secure_filename(file.filename)
    file.save(os.path.join(target_dir, new_filename))

    url_publik = f"https://{BASE_PUBLIC_URL}/files/{category}/{new_filename}"
    return jsonify({
        'message': f"Berhasil Update !",
        'url': url_publik
    }), 200

## Delete
@app.route('/delete/<category>/<filename>', methods=['DELETE'])
def delete_file(category, filename):
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori tidak valid !'}), 400
    
    target_dir = os.path.join(BASE_UPLOAD_FOLDER, category)
    file_path = os.path.join(target_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({
            'message': f"Berhasil menghapus file{filename} di kategori {category}",
        }), 200
    else:
        return jsonify({
            'error': "File tidak ditemukan !"
        }), 400
    
@app.after_request
def app_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)