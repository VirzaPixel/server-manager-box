import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

## url
BASE_PUBLIC_URL = os.environ.get('BASE_PUBLIC_URL', '')

## folder
folders_raw = os.environ.get('BASE_UPLOAD_FOLDER', '')
folders_raw = folders_raw.replace('"', '').replace("'", "")
BASE_UPLOAD_FOLDER = [f.strip() for f in folders_raw.split(',') if f.strip()]

## category
categories_raw = os.environ.get('ALLOWED_CATEGORIES', '')
ALLOWED_CATEGORIES = [c.strip() for c in categories_raw.split(',') if c.strip()]

## max file length
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

for folder in BASE_UPLOAD_FOLDER:
    if not os.path.exists(folder):
        os.makedirs(folder)
    for category in ALLOWED_CATEGORIES:
        category_path = os.path.join(folder, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)

## Read
@app.route('/files/<category>/<filename>', methods=['GET'], defaults={'folder': 'alfal'})
@app.route('/files/<folder>/<category>/<filename>', methods=['GET'])
def get_new_file(folder, category, filename):
    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': f'Folder utama ({folder}) tidak valid'}), 400 
    
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': f'Kategory tidak valid !'}), 400
    
    target_dir = os.path.join(folder, category)

    return send_from_directory(target_dir, filename)

## Create
@app.route('/upload/<folder>/<category>', methods=['POST'])
def upload_file(folder, category):
    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid'}), 400

    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori folder tidak valid !'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Name file kosong'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        target_dir = os.path.join(folder, category)

        # save file to folder
        file.save(os.path.join(target_dir, filename))

        url_publik = f"https://{BASE_PUBLIC_URL}/files/{folder}/{category}/{filename}"

        return jsonify({
            'message': f"Upload ke {category} Berhasil !",
            'url' : url_publik
        }), 200
    
## Create old format
@app.route('/upload/<category>', methods=['POST'])
def old_upload_file(category):
    return upload_file(folder='alfal', category=category)

## Update
@app.route('/update/<folder>/<category>/<filename>', methods=['PUT'])
def update_file(folder, category, filename):

    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid !'}), 400

    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori tidak Valid !'}), 400
    
    target_dir = os.path.join(folder, category)
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File tidak ditemukan !'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']

    os.remove(file_path)
    new_filename = secure_filename(file.filename)
    file.save(os.path.join(target_dir, new_filename))

    url_publik = f"https://{BASE_PUBLIC_URL}/files/{folder}/{category}/{new_filename}"
    return jsonify({
        'message': f"Berhasil Update !",
        'url': url_publik
    }), 200

## Update old format
@app.route('/update/<category>/<filename>', methods=['PUT'])
def update_file_old(category, filename):
    return update_file(folder='alfal', category=category, filename=filename)

## Delete
@app.route('/delete/<folder>/<category>/<filename>', methods=['DELETE'])
def delete_file(folder, category, filename):

    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid'}), 400
    
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'error': 'Kategori tidak valid !'}), 400
    
    target_dir = os.path.join(folder, category)
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
    
## Delete old format
@app.route('/delete/<category>/<filename>', methods=['DELETE'])
def delete_file_old(category, filename):
    return delete_file(folder='alfal', category=category, filename=filename)

    
@app.after_request
def app_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)