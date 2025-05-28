import os
import uuid
import concurrent.futures
from flask import Flask, render_template, request, jsonify, send_from_directory
from logic import convert_file

app = Flask(__name__)

# Definimos las rutas para las carpetas temporales de subida y conversión
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CONVERSIONS_FOLDER = 'conversions'
if not os.path.exists(CONVERSIONS_FOLDER):
    os.makedirs(CONVERSIONS_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERSIONS_FOLDER'] = CONVERSIONS_FOLDER

# Executor para tareas en segundo plano
executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) # Usar número de CPUs como workers
tasks = {} # Diccionario para seguir el estado de las tareas futuras

# Rutas de apoyo para favicon
@app.route('/favicon.png')
def favicon_png():
    return send_from_directory('static', 'favicon.png')

@app.route('/favicon.ico')
def favicon_ico():
    return send_from_directory('static', 'favicon.ico')

# Ruta principal para la interfaz de usuario
@app.route('/')
def index():
    # Opciones de formato ampliadas para vídeos e imágenes.
    video_formats = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'] # Formatos de vídeo ampliados
    image_formats = ['jpg', 'png', 'webp', 'gif', 'bmp', 'tiff'] # Formatos de imagen ampliados
    return render_template('index.html', video_formats=video_formats, image_formats=image_formats)

# Endpoint principal para conversión de archivos
@app.route('/convert', methods=['POST'])
def convert():
    files = request.files.getlist('files')
    target_format = request.form.get('target_format')
    quality_level = request.form.get('quality_level', 75, type=int)

    print(f"\n--- Nueva solicitud /convert ---") # LOG INICIO SOLICITUD
    print(f"Archivos recibidos: {[f.filename for f in files]}") # LOG ARCHIVOS
    print(f"Formato destino: {target_format}, Calidad: {quality_level}") # LOG PARAMS

    if not files or not any(f.filename for f in files):
        print("ERROR: No se recibieron archivos o nombres de archivo vacíos.") # LOG ERROR
        return jsonify({'status': 'error', 'message': 'Debe seleccionar al menos un archivo.'})
    if not target_format:
        print("ERROR: No se seleccionó formato de salida.") # LOG ERROR
        return jsonify({'status': 'error', 'message': 'Debe seleccionar un formato de salida.'})
    if not 1 <= quality_level <= 100:
        print(f"ERROR: Nivel de calidad inválido: {quality_level}") # LOG ERROR
        return jsonify({'status': 'error', 'message': 'El nivel de calidad debe estar entre 1 y 100.'})

    results = []
    for file in files:
        original_filename = file.filename
        if not original_filename:
            print("Saltando archivo: Nombre de archivo vacío.") # LOG SALTO
            continue

        print(f"\nProcesando archivo: {original_filename}") # LOG ARCHIVO INDIVIDUAL
        print(f"  MIME type reportado: {file.mimetype}") # LOG MIME

        unique_id = uuid.uuid4().hex
        input_filename = f"{unique_id}_{original_filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)

        try:
            print(f"  Guardando en: {input_path}") # LOG GUARDAR
            file.save(input_path)
            print(f"  Guardado con éxito.") # LOG GUARDADO OK
        except Exception as e:
             print(f"  ERROR al guardar archivo {original_filename}: {e}") # LOG ERROR GUARDAR
             continue # Saltar este archivo si no se pudo guardar

        # Determinar tipo
        mime = file.mimetype
        is_video = None
        file_type_determined_by = "Desconocido"

        # Listas de extensiones válidas
        video_exts = ['.mp4', '.m4v', '.avi', '.mkv', '.mov', '.wmv',
                      '.flv', '.webm', '.mpg', '.mpeg', '.3gp']

        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
                      '.tiff', '.tif', '.heic', '.heif']
        
        audio_exts = ['.mp3','.aac','.m4a','.wav','.flac','.ogg','.opus',
                      '.wma']

        if mime:
            if mime.startswith('video'):
                is_video = True
                file_type_determined_by = "MIME (video)"
            elif mime.startswith('image'):
                is_video = False
                file_type_determined_by = "MIME (image)"
            elif mime.startswith('audio'):
                is_video = False
                file_type_determined_by = "MIME (audio)"

        if is_video is None: # En caso de que MIME no sea concluyente
            _, ext = os.path.splitext(original_filename)
            ext = ext.lower()
            print(f"  MIME no concluyente, comprobando extensión: '{ext}'") # LOG EXTENSION
            if ext in video_exts:
                is_video = True
                file_type_determined_by = f"Extensión ({ext} - video)"
            elif ext in image_exts:
                is_video = False
                file_type_determined_by = f"Extensión ({ext} - image)"
            elif ext in audio_exts:
                is_video = False
                file_type_determined_by = f"Extensión ({ext} - audio)"

        if is_video is None: # Si ni MIME ni extensión funcionaron
            print(f"  SALTANDO archivo: Tipo no reconocido (MIME: '{mime}', Ext: '{ext}')") # LOG SALTO TIPO
            try:
                os.remove(input_path) # Limpiar
            except OSError as e:
                print(f"  Advertencia: No se pudo eliminar archivo saltado {input_path}: {e}")
            continue # Saltar la conversión

        print(f"  Tipo determinado: {'Video' if is_video else 'Imagen'} (por {file_type_determined_by})") # LOG TIPO OK

        # ... (resto del código para crear nombre salida, lanzar tarea, etc.) ...
        base, _ = os.path.splitext(original_filename)
        safe_base = "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in base).rstrip()
        output_filename = f"{safe_base}_converted.{target_format}"
        output_path = os.path.join(app.config['CONVERSIONS_FOLDER'], output_filename)

        print(f"  Preparando tarea: {input_path} -> {output_path}") # LOG TAREA

        future = executor.submit(convert_file, input_path, output_path, is_video, quality_level, target_format)
        task_id = uuid.uuid4().hex
        tasks[task_id] = {'future': future, 'input_file': original_filename, 'output_file': output_filename}
        results.append({'task_id': task_id, 'input_file': original_filename, 'output_file': output_filename})

        print(f"  Tarea {task_id} añadida.") # LOG TAREA OK

    print(f"\nProcesamiento de archivos terminado. Tareas válidas creadas: {len(results)}") # LOG FIN BUCLE
    if not results:
         print("ERROR FINAL: No se crearon tareas válidas.") # LOG ERROR FINAL
         return jsonify({'status': 'error', 'message': 'No se seleccionaron archivos válidos para conversión.'})

    print("Tareas finalizadas correctamente.") # LOG OK
    return jsonify({'status': 'ok', 'tasks': results})

# Ruta para consultar el estado de una tarea (polling desde el front-end)
@app.route('/task_status/<string:task_id>') # ID es string (UUID)
def task_status(task_id):
    task_info = tasks.get(task_id)
    if task_info is None:
        return jsonify({'status': 'error', 'message': 'Tarea no encontrada.'}), 404

    future = task_info['future']
    if future.done():
        try:
            success, file_in_uuid, info_or_path = future.result()
            return jsonify({
                'status': 'done',
                'success': success,
                'file': task_info['input_file'], # Devolver nombre original
                'info': info_or_path if not success else os.path.basename(info_or_path) # Devolver nombre o error
            })
        except Exception as e:
            # Capturar excepciones que pudieron ocurrir dentro de la tarea
            print(f"Exception in task {task_id}: {e}")
            return jsonify({
                'status': 'done',
                'success': False,
                'file': task_info['input_file'],
                'info': f"Error interno en la tarea: {e}"
            })
    else:
        return jsonify({'status': 'running'})
    
# Ruta para servir archivos convertidos
@app.route('/converted/<path:filename>')
def converted_file(filename):
    """
    Devuelve el archivo recién convertido para que el front-end pueda incrustarlo
    (video/img) como vista previa.
    """
    return send_from_directory(app.config['CONVERSIONS_FOLDER'], filename)

# Ruta para descargar archivos convertidos
@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Devuelve el archivo convertido como adjunto para forzar descarga.
    """
    try:
        return send_from_directory(
            app.config['CONVERSIONS_FOLDER'],
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'Archivo no encontrado.'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Ejecutar en todas las interfaces para acceso en red local si es necesario