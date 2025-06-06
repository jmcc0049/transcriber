import os
import ffmpeg
import tempfile
import subprocess  # Usar subprocess puede dar más control y mejor manejo de errores

# --- Listas de extensiones ----------------------------------
AUDIO_EXTS = {'.mp3', '.aac', '.m4a', '.wav', '.flac', '.ogg', '.opus', '.wma', '.flac', '.wav'}

def heif_to_png(src):
    """
    Convierte un HEIC/HEIF a PNG usando heif-convert y devuelve
    la ruta del PNG temporal (caller debe borrarlo). Devuelve None en error.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()                       # cerramos para que heif-convert pueda escribir
    cmd = ['heif-convert', src, tmp.name]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return tmp.name
    except subprocess.CalledProcessError as e:
        os.remove(tmp.name)
        print(f"heif-convert falló con código {e.returncode}")
        return None

def _bitrate_from_quality(q: int, minimum: int, maximum: int) -> int:
    """Mapa lineal del *quality_level* (1‑100) a un bitrate en kbit/s."""
    return int(minimum + (q - 1) * (maximum - minimum) / 99)

def convert_file(input_file, output_file, is_video, quality_level, target_format):
    """
    Realiza la conversión utilizando ffmpeg, ajustando la calidad según quality_level (1-100)
    y usando el target_format especificado.
    Devuelve (True, input_file, output_path) en éxito o (False, input_file, error_message) en fallo.
    """
    print(f"Iniciando conversión: {input_file} -> {output_file} (Video: {is_video}, Calidad: {quality_level}, Formato: {target_format})")

    # Asegurarse de que la carpeta de destino exista
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    except OSError as e:
        error_msg = f"Error creando directorio de salida: {e}"
        print(error_msg)
        return False, os.path.basename(input_file), error_msg

    output_options = {}
    global_options = ['-hide_banner', '-loglevel', 'error']

    # --- HEIC/HEIF fallback ---------------------------------
    ext = os.path.splitext(input_file)[1].lower()
    temp_image = None  # para limpieza al final

    # Solo para imágenes, no vídeo
    if not is_video and ext in ('.heic', '.heif'):
        temp_image = heif_to_png(input_file)
        if temp_image is None:
            return (False, os.path.basename(input_file),
                    "heif-convert no pudo recomponer la imagen.")
        input_for_ffmpeg = temp_image  # usamos el PNG
    else:
        input_for_ffmpeg = input_file
    # --------------------------------------------------------

    fmt_out = target_format.lower()

    if is_video:
        # Mapeo de extensiones a contenedores FFmpeg
        fmt = target_format.lower()
        if fmt == 'wmv':
            output_options['format'] = 'asf'
            # Para alta calidad
            output_options['vcodec'] = 'wmv2'
            output_options['acodec'] = 'wmav2'
            # Ajustar bitrate de vídeo según calidad (opcional)
            min_br, max_br = 500, 2500  # en kbit/s
            v_bitrate = int(min_br + (quality_level - 1) * (max_br - min_br) / 99)
            output_options['video_bitrate'] = f"{v_bitrate}k"
            # Ajustar bitrate de audio
            min_ab, max_ab = 64, 192
            a_bitrate = int(min_ab + (quality_level - 1) * (max_ab - min_ab) / 99)
            output_options['audio_bitrate'] = f"{a_bitrate}k"
        elif fmt == 'webm':
            output_options['format'] = 'webm'
            output_options['vcodec'] = 'libvpx-vp9'
            # Asigna bitrate según el deslizador de calidad (kbit/s)
            min_br, max_br = 500, 3500
            v_bitrate = int(min_br + (quality_level - 1) * (max_br - min_br) / 99)
            output_options['video_bitrate'] = f'{v_bitrate}k'
            output_options['acodec'] = 'libopus'      # audio Opus
            min_ab, max_ab = 64, 192
            a_bitrate = int(min_ab + (quality_level - 1) * (max_ab - min_ab) / 99)
            output_options['audio_bitrate'] = f'{a_bitrate}k'
            # WebM no necesita pix_fmt específico, pero yuv420p es seguro
            output_options['pix_fmt'] = 'yuv420p'
        else:
            # Para mkv usa matroska; el resto directamente
            output_options['format'] = 'matroska' if fmt == 'mkv' else target_format
            # Mapeo de Calidad (1-100) a CRF para libx264
            min_crf, max_crf = 18, 35
            crf_value = round(max_crf - (quality_level - 1) * (max_crf - min_crf) / 99)
            output_options['crf'] = crf_value
            # Utilizamos H.264 como códec de vídeo por defecto
            output_options['vcodec'] = 'libx264'
            output_options['preset'] = 'fast'
            # Audio en AAC
            output_options['acodec'] = 'aac'
            min_ab, max_ab = 64, 192
            a_bitrate = int(min_ab + (quality_level - 1) * (max_ab - min_ab) / 99)
            output_options['audio_bitrate'] = f"{a_bitrate}k"
            # Formato de píxeles seguro
            output_options['pix_fmt'] = 'yuv420p'

        stream = ffmpeg.input(input_for_ffmpeg)
        output_stream = ffmpeg.output(stream.video, stream.audio, output_file, **output_options)
    elif ext in AUDIO_EXTS or fmt_out in {e.lstrip(".") for e in AUDIO_EXTS}:
        stream = ffmpeg.input(input_for_ffmpeg)
        output_options["vn"] = None  # Fuerza no incluir vídeo

        # Asignar códec/bitrate según formato
        if fmt_out == "mp3":
            output_options.update({
                "acodec": "libmp3lame",
                "audio_bitrate": f"{_bitrate_from_quality(quality_level, 64, 320)}k",
            })
        elif fmt_out in {"aac", "m4a"}:
            output_options.update({
                "acodec": "aac",
                "audio_bitrate": f"{_bitrate_from_quality(quality_level, 64, 320)}k",
            })
        elif fmt_out == "ogg":
            output_options.update({
                "acodec": "libvorbis",
                "audio_bitrate": f"{_bitrate_from_quality(quality_level, 64, 320)}k",
            })
        elif fmt_out == "opus":
            output_options.update({
                "acodec": "libopus",
                "audio_bitrate": f"{_bitrate_from_quality(quality_level, 48, 256)}k",
            })
        elif fmt_out == "wma":
            output_options.update({
                "acodec": "wmav2",
                "audio_bitrate": f"{_bitrate_from_quality(quality_level, 64, 192)}k",
            })
        elif fmt_out == "flac":
            # FLAC es sin pérdida; mapeamos calidad a compression_level 0‑8
            comp_lvl = round((quality_level / 100) * 8)
            output_options.update({"acodec": "flac", "compression_level": comp_lvl})
        elif fmt_out == "wav":
            output_options.update({"acodec": "pcm_s16le"})  # WAV PCM 16‑bit LE
        else:
            return False, os.path.basename(input_file), f"Formato de audio no soportado: {target_format}"

        output_stream = ffmpeg.output(stream.audio, output_file, **output_options)
    else:
        stream = ffmpeg.input(input_for_ffmpeg)
        fmt_lower = target_format.lower()

        # Asegurar que no se fuerce un formato de contenedor erróneo (como -f png)
        output_options.pop('format', None)  # evitar errores como "format 'png' is not known"

        if fmt_lower in ['jpg', 'jpeg']:
            min_q = 2
            max_q = 31
            qscale_value = round(max_q - (quality_level - 1) * (max_q - min_q) / 99)
            output_options['qscale:v'] = qscale_value
            output_options['vcodec'] = 'mjpeg'

        elif fmt_lower == 'webp':
            output_options['quality'] = quality_level

        elif fmt_lower == 'png':
            compression_level = round((quality_level / 100) * 100)
            output_options['compression_level'] = compression_level

        elif fmt_lower == 'gif':
            pass  # GIF no requiere calidad directamente

        elif fmt_lower == 'bmp':
            output_options['pix_fmt'] = 'rgb24'

        elif fmt_lower == 'tiff':
            output_options['compression_algo'] = 'lzw'

        output_stream = ffmpeg.output(stream, output_file, **output_options)

    try:
        args = ffmpeg.compile(output_stream, overwrite_output=True)
        args = ['ffmpeg'] + global_options + args[1:]
        print(f"Ejecutando FFmpeg con comando: {' '.join(args)}")

        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode('utf-8', errors='ignore').strip()
            print(f"Error de FFmpeg (código {process.returncode}): {error_message}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError as e:
                    print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e}")
            return False, os.path.basename(input_file), f"Error en FFmpeg: {error_message}"
        else:
            print(f"Archivo convertido exitosamente: {output_file}")
            try:
                os.remove(input_file)
                if temp_image and os.path.exists(temp_image):
                    os.remove(temp_image)
                print(f"Archivo de entrada eliminado: {input_file}")
            except OSError as e:
                print(f"Advertencia: No se pudo eliminar el archivo de entrada {input_file}: {e}")
            return True, os.path.basename(input_file), output_file

    except ffmpeg.Error as e:
        stderr_decoded = e.stderr.decode('utf-8', errors='ignore').strip() if e.stderr else "No stderr available"
        print(f"Error de ffmpeg-python: {stderr_decoded}")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except OSError as e_rm:
                print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e_rm}")
        return False, os.path.basename(input_file), f"Error en FFmpeg (compile/setup): {stderr_decoded}"

    except Exception as e:
        error_msg = f"Error inesperado durante la conversión: {str(e)}"
        print(error_msg)
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except OSError as e_rm:
                print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e_rm}")
        return False, os.path.basename(input_file), error_msg