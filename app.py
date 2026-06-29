import os
from functools import wraps
from flask_cors import CORS
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

app = Flask(__name__)

CORS(app)

## supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", '')
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", '')
supabase: Client = None

## api key
API_KEY = os.environ.get("API_KEY", '')

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

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Berhasil Terkoneksi ke Supabase")
    except Exception as e:
        print(f"Tidak berhasil Terkoneksi ke Supabase: {e}")

for folder in BASE_UPLOAD_FOLDER:
    if not os.path.exists(folder):
        os.makedirs(folder)
    for category in ALLOWED_CATEGORIES:
        category_path = os.path.join(folder, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)

## api key validator
def require_api_key(f):
    @wraps(f)
    def validator_func(*args, **kwargs):
        user_api_key = request.headers.get("X-API-KEY")

        if not user_api_key:
            return jsonify({'error': 'Api key tidak ditemukan !'}), 401
        elif user_api_key != API_KEY:
            return jsonify({'error': 'Api key salah !'}), 403
        
        return f(*args, **kwargs)
    
    return validator_func

## Read
@app.route('/files/<category>/<filename>', methods=['GET'])
def get_file(category, filename):
    
    target_dir = os.path.join('alfal', category)
    return send_from_directory(target_dir, filename)


## Read new format
@app.route('/files/<folder>/<category>/<filename>', methods=['GET'])
def get_new_file(folder, category, filename):
    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': f'Folder utama ({folder}) tidak valid'}), 400

    target_dir = os.path.join(folder, category)
    return send_from_directory(target_dir, filename)

## Create
@app.route('/upload/<folder>/<category>', methods=['POST'])
@require_api_key
def upload_file(folder, category):
    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid'}), 400

    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Name file kosong'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        target_dir = os.path.join(folder, category)
        file_path = os.path.join(target_dir, filename)

        # save file to folder
        file.save(file_path)

        url_publik = f"https://{BASE_PUBLIC_URL}/files/{folder}/{category}/{filename}"

        file_size = os.path.getsize(file_path)

        if supabase:
            try:
                ## delete duplicate filename
                supabase.table("files").delete().eq("name", filename).eq("folder", folder).eq("category", category).execute()
                supabase.table("files").insert({
                    "name": filename,
                    "url": url_publik,
                    "folder": folder,
                    "category": category,
                    "size_bytes": file_size
                }).execute()
            except Exception as e:
                print(f"Gagal menambah data: {e}")
            
        return jsonify({
            'message': f"Upload ke {category} Berhasil !",
            'url' : url_publik
        }), 200
    
## Create old format
@app.route('/upload/<category>', methods=['POST'])
@require_api_key
def old_upload_file(category):
    return upload_file(folder='alfal', category=category)

## Update
@app.route('/update/<folder>/<category>/<filename>', methods=['PUT'])
@require_api_key
def update_file(folder, category, filename):

    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid !'}), 400

    
    target_dir = os.path.join(folder, category)
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File tidak ditemukan !'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang dikirim !'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Name file baru kosong'}), 400

    os.remove(file_path)
    
    new_filename = secure_filename(file.filename)
    new_file_path = os.path.join(target_dir, new_filename)
    file.save(new_file_path)

    url_publik = f"https://{BASE_PUBLIC_URL}/files/{folder}/{category}/{new_filename}"

    new_file_size = os.path.getsize(new_file_path)

    if supabase:
        try:
            ## delete duplicate file
            supabase.table("files").delete().eq("name", filename).eq("folder", folder).eq("category", category).execute()
            supabase.table("files").insert({
                "name": new_filename,
                "url": url_publik,
                "folder": folder,
                "category": category,
                "size_bytes": new_file_size
            }).execute()
        except Exception as e:
            print(f"Gagal Update data: {e}")    

    return jsonify({
        'message': f"Berhasil Update !",
        'url': url_publik
    }), 200

## Update old format
@app.route('/update/<category>/<filename>', methods=['PUT'])
@require_api_key
def update_file_old(category, filename):
    return update_file(folder='alfal', category=category, filename=filename)

## Delete
@app.route('/delete/<folder>/<category>/<filename>', methods=['DELETE'])
@require_api_key
def delete_file(folder, category, filename):

    if folder not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder utama tidak valid'}), 400
    
    target_dir = os.path.join(folder, category)
    file_path = os.path.join(target_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)

        if supabase:
            try:
                supabase.table("files").delete().eq("name", filename).eq("folder", folder).eq("category", category).execute()
            except Exception as e:
                print(f"Gagal Menghapus file{e}")
            
        return jsonify({
            'message': f"Berhasil menghapus file {filename} di kategori {category}",
        }), 200
    
    else:
        return jsonify({
            'error': "File tidak ditemukan !"
        }), 400
    
## Delete old format
@app.route('/delete/<category>/<filename>', methods=['DELETE'])
@require_api_key
def delete_file_old(category, filename):
    return delete_file(folder='alfal', category=category, filename=filename)
    
## Get Folder
@app.route('/folder/<folder_name>/categories', methods=['GET'])
def get_folder_categories(folder_name):
    
    if folder_name not in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'folder tidak valid'})
    
    folder_path = os.path.join(folder_name)

    if not os.path.exists(folder_path):
        return jsonify({'error': 'folder tidak ditemukan'})
    
    try:
        categories = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                categories.append({
                    'name': item, 
                    'file_count': file_count
                })
        
        categories.sort(key=lambda x: x['name'])

        return jsonify({
            'folder': folder_name,
            'categories': categories,
            'total_categories': len(categories)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Gagal membaca folder: {e}'}), 500


## Create New Folder
@app.route('/folder/create/<folder_name>', methods=['POST'])
@require_api_key
def create_folder(folder_name):
    folder_name = folder_name.strip()

    if not folder_name:
        return jsonify({'error': 'Folder name tidak boleh kosong'}), 400
    
    if folder_name in BASE_UPLOAD_FOLDER:
        return jsonify({'error': 'Folder sudah ada'}), 400
    
    folder_path = os.path.join(folder_name)

    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_path, exist_ok=True)

        for category in ALLOWED_CATEGORIES:
            category_path = os.path.join(folder_path, category)
            os.makedirs(category_path, exist_ok=True)

        return jsonify({
            'message': 'Berhasil membuat folder',
            'folder': folder_name
        }), 200
    except Exception as e:
        return jsonify({'error': f'Gagal membuat folder: {str(e)}'}), 500

## skipping ngrok web secure
@app.after_request
def app_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

### Disable Auto-Sync.

## auto sync for automatic rewrite the 
# def sync_files():
#     if not supabase:
#         return 
#     print("Memulai Auto-Sync...")
#     for folder in BASE_UPLOAD_FOLDER:
#         for category in ALLOWED_CATEGORIES:
#             target_dir = os.path.join(folder, category)
#             if not os.path.exists(target_dir):
#                 continue

#             files_in_folder = os.listdir(target_dir)
#             for filename in files_in_folder:
#                 file_path = os.path.join(target_dir, filename)
#                 if os.path.isdir(file_path):
#                     continue
#                 try:
#                     response = supabase.table("files").select("id").eq("name", filename).eq("folder", folder).eq("category", category).execute()
#                     if not response.data:
#                         file_size = os.path.getsize(file_path)
                    
#                         url_publik = f"https://{BASE_PUBLIC_URL}/files/{folder}/{category}/{filename}"

#                         supabase.table("files").insert({
#                             "name": filename,
#                             "url": url_publik,
#                             "folder": folder,
#                             "category": category,
#                             "size_bytes": file_size
#                         }).execute()
#                         print(f"Auto-Sync: Berhasil mendaftarkan {filename}")
#                 except Exception as e:
#                     print(f"Gagal Auto-sync: {e}")

## health check
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'Storage Manager API is running',
        'folders': BASE_UPLOAD_FOLDER,
        'categories': ALLOWED_CATEGORIES
    }), 200

# configures the debug True for workflows working
if __name__ == "__main__":
    # sync_files()
    app.run(host='0.0.0.0', port=8000, debug=False)