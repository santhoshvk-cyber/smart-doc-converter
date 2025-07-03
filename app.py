from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import os
import uuid
import logging
import time
from werkzeug.utils import secure_filename
from pdf2docx import Converter
import pypandoc

# ========== Config ==========
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.secret_key = 'secret@123'

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)

# ========== Create Folders ==========
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# ========== Helper Functions ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_filename(extension):
    return f"{uuid.uuid4().hex}.{extension}"

def clean_old_files(folder, age_limit=600):
    now = time.time()
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        if os.path.isfile(path) and now - os.path.getmtime(path) > age_limit:
            os.remove(path)

# ========== Routes ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_file():
    file = request.files.get('file')
    conversion_type = request.form.get('conversion_type')

    if not file or file.filename == '':
        flash('No file selected.')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Unsupported file type.')
        return redirect(url_for('index'))

    clean_old_files(UPLOAD_FOLDER)
    clean_old_files(CONVERTED_FOLDER)

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], generate_filename(ext))
    file.save(input_path)

    output_ext = 'pdf' if conversion_type == 'word-to-pdf' else 'docx'
    output_filename = generate_filename(output_ext)
    output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    try:
        if conversion_type == 'word-to-pdf':
            # Use pypandoc instead of docx2pdf
            pypandoc.convert_file(input_path, 'pdf', outputfile=output_path)

        elif conversion_type == 'pdf-to-word':
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
        else:
            flash('Invalid conversion type.')
            return redirect(url_for('index'))

        return render_template('result.html', download_file=output_filename)

    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        flash('Conversion failed. Please try a different file.')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        flash('File not found or expired.')
        return redirect(url_for('index'))

# ========== Run ==========
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
