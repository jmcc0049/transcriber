import os
import ffmpeg
import subprocess  # Usar subprocess puede dar más control y mejor manejo de errores

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

    if is_video:
        output_options['format'] = target_format

        # Mapeo de Calidad (1-100) a CRF (para libx264)
        min_crf = 18
        max_crf = 35
        crf_value = round(max_crf - (quality_level - 1) * (max_crf - min_crf) / 99)
        output_options['crf'] = crf_value
        output_options['vcodec'] = 'libx264'
        output_options['acodec'] = 'aac'
        output_options['preset'] = 'fast'

        min_audio_br = 64
        max_audio_br = 192
        audio_bitrate = int(min_audio_br + (quality_level - 1) * (max_audio_br - min_audio_br) / 99)
        output_options['audio_bitrate'] = f"{audio_bitrate}k"
        output_options['pix_fmt'] = 'yuv420p'

        stream = ffmpeg.input(input_file)
        output_stream = ffmpeg.output(stream.video, stream.audio, output_file, **output_options)

    else:
        stream = ffmpeg.input(input_file)
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