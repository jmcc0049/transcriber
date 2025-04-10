import os

import uuid
import concurrent.futures
from flask import Flask, render_template, request, jsonify
from logic import convert_file

app = Flask(__name__)

# Definimos las rutas para las carpetas temporales de subida y conversión
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CONVERSIONS_FOLDER = 'conversions'
if not os.path.exists(CONVERSIONS_FOLDER):
    os.makedirs(CONVERSIONS_FOLDER)

# Executor para tareas en segundo plano
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
tasks = {}


@app.route('/')
def index():
    # Opciones de formato para vídeos e imágenes.
    video_formats = ['mp4', 'avi', 'mkv']
    image_formats = ['jpg', 'png', 'webp']
    return render_template('index.html', video_formats=video_formats, image_formats=image_formats)


@app.route('/convert', methods=['POST'])
def convert():
    # Se obtienen los archivos subidos
    files = request.files.getlist('files')
    target_format = request.form.get('target_format')
    if not files or not target_format:
        return jsonify({'status': 'error', 'message': 'Debe seleccionar al menos un archivo y un formato de salida.'})

    results = []
    for file in files:
        # Generar un nombre único para evitar conflictos
        unique_id = uuid.uuid4().hex
        input_filename = unique_id + "_" + file.filename
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        file.save(input_path)

        # Determinar si el archivo es vídeo o imagen según el MIME type
        mime = file.mimetype
        if mime.startswith('video'):
            is_video = True
        elif mime.startswith('image'):
            is_video = False
        else:
            # Si por alguna razón se envía otro tipo, se salta la conversión.
            continue

        # Definir el nombre de salida usando la extensión seleccionada
        base, _ = os.path.splitext(file.filename)
        output_filename = f"{base}_converted.{target_format}"
        output_path = os.path.join(CONVERSIONS_FOLDER, output_filename)

        # Lanzar la conversión en segundo plano
        future = executor.submit(convert_file, input_path, output_path, is_video, CONVERSIONS_FOLDER)
        task_id = id(future)
        tasks[task_id] = future
        results.append({'task_id': task_id, 'input_file': file.filename, 'output_file': output_filename})

    return jsonify({'status': 'ok', 'tasks': results})


@app.route('/task_status/<int:task_id>')
def task_status(task_id):
    future = tasks.get(task_id)
    if future is None:
        return jsonify({'status': 'error', 'message': 'Tarea no encontrada.'})
    if future.done():
        success, file_in, info = future.result()
        return jsonify({'status': 'done', 'success': success, 'file': file_in, 'info': info})
    else:
        return jsonify({'status': 'running'})


if __name__ == '__main__':
    app.run(debug=True)