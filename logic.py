import os
import ffmpeg
import subprocess # Usar subprocess puede dar más control y mejor manejo de errores a veces

def convert_file(input_file, output_file, is_video, quality_level, target_format):
    """
    Realiza la conversión utilizando ffmpeg, ajustando la calidad según quality_level (1-100)
    y usando el target_format especificado.
    Devuelve (True, output_path) en éxito o (False, error_message) en fallo.
    """
    print(f"Iniciando conversión: {input_file} -> {output_file} (Video: {is_video}, Calidad: {quality_level}, Formato: {target_format})")

    # Asegurarse de que la carpeta de destino exista
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    except OSError as e:
        error_msg = f"Error creando directorio de salida: {e}"
        print(error_msg)
        # No eliminar input_file aquí, podría estar usándose en otro hilo
        return False, error_msg

    output_options = {'format': target_format}
    global_options = ['-hide_banner', '-loglevel', 'error'] # Opciones globales para menos salida, loguear solo errores

    if is_video:
        # --- Configuración para Vídeo ---
        # Mapeo de Calidad (1-100) a CRF (para libx264: ~18=alta, ~28=media, ~35=baja)
        # Calidad 1 -> CRF 35, Calidad 100 -> CRF 18
        # Fórmula: crf = MaxCRF - (Quality - 1) * (MaxCRF - MinCRF) / 99
        min_crf = 18
        max_crf = 35
        crf_value = round(max_crf - (quality_level - 1) * (max_crf - min_crf) / 99)
        output_options['crf'] = crf_value

        # Códecs (ejemplo: libx264/aac; podrían necesitar ajustes por formato)
        output_options['vcodec'] = 'libx264'
        output_options['acodec'] = 'aac' # Códec de audio común

        # Preset: afecta velocidad vs compresión (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        output_options['preset'] = 'fast' # Un buen balance

        # Audio Bitrate: también puede escalar con calidad (e.g., 64k a 192k)
        min_audio_br = 64
        max_audio_br = 192
        audio_bitrate = int(min_audio_br + (quality_level - 1) * (max_audio_br - min_audio_br) / 99)
        output_options['audio_bitrate'] = f"{audio_bitrate}k"

        # Pixel format para compatibilidad (especialmente con reproductores antiguos/QuickTime)
        output_options['pix_fmt'] = 'yuv420p'

        # Quitar escalado por defecto de la versión anterior
        # video = stream.video.filter('scale', 1280, 720) # Eliminado

        stream = ffmpeg.input(input_file)
        # Aplicar opciones al stream de salida
        output_stream = ffmpeg.output(stream.video, stream.audio, output_file, **output_options)

    else:
        # --- Configuración para Imagen ---
        stream = ffmpeg.input(input_file)
        fmt_lower = target_format.lower()

        if fmt_lower in ['jpg', 'jpeg']:
            # Mapeo Calidad (1-100) a qscale:v (para mjpeg: 2=casi lossless, 31=peor)
            # Calidad 1 -> qscale 31, Calidad 100 -> qscale 2
            min_q = 2
            max_q = 31
            qscale_value = round(max_q - (quality_level - 1) * (max_q - min_q) / 99)
            output_options['qscale:v'] = qscale_value
            # Forzar códec MJPEG para JPG
            output_options['vcodec'] = 'mjpeg'

        elif fmt_lower == 'webp':
            # WebP usa -quality (0-100), mapeo directo.
            # También tiene -lossless (0 o 1) y -compression_level (0-6)
            output_options['quality'] = quality_level
            # Podrías añadir opción para lossless si quality=100, etc.

        elif fmt_lower == 'png':
            # PNG es lossless. 'quality' no aplica directamente.
            # Se puede ajustar 'compression_level' (0-100 en ffmpeg moderno, 0=rápido/grande, 100=lento/pequeño)
            # Mapeamos Calidad a nivel de compresión (calidad alta = compresión alta)
            compression_level = round((quality_level / 100) * 100)
            output_options['compression_level'] = compression_level
            # Asegurar formato de pixel compatible si es necesario, ej. 'rgba' o 'rgb24'
            # output_options['pix_fmt'] = 'rgba'

        elif fmt_lower == 'gif':
            # GIF tiene paleta limitada. La conversión requiere filtros complejos para buen resultado.
            # Ejemplo simple sin optimización de paleta:
            pass # Usar ffmpeg por defecto, calidad no aplica directamente

        elif fmt_lower == 'bmp':
            # BMP es sin compresión usualmente. Calidad no aplica.
            # Asegurar formato de pixel como rgb24 o bgr24
            output_options['pix_fmt'] = 'rgb24'

        elif fmt_lower == 'tiff':
            # TIFF puede tener compresión (lossless como LZW, Deflate, o lossy como JPEG)
            # Ejemplo con compresión LZW (lossless)
            output_options['compression_algo'] = 'lzw'


        # Aplicar opciones al stream de salida
        output_stream = ffmpeg.output(stream, output_file, **output_options)


    # --- Ejecución de FFmpeg ---
    try:
        # Construir y ejecutar el comando
        # .compile() genera los argumentos para subprocess
        args = ffmpeg.compile(output_stream, overwrite_output=True)
        # Añadir opciones globales al inicio
        args = ['ffmpeg'] + global_options + args[1:] # Reemplazar el 'ffmpeg' compilado con el nuestro + globales

        print(f"Ejecutando FFmpeg con comando: {' '.join(args)}") # Log del comando
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            # Hubo un error
            error_message = stderr.decode('utf-8', errors='ignore').strip()
            print(f"Error de FFmpeg (código {process.returncode}): {error_message}")
            # Intentar limpiar archivo de salida fallido si existe
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError as e:
                     print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e}")
            # No eliminar input_file aquí
            return False, f"Error en FFmpeg: {error_message}"
        else:
            # Éxito
            success_message = f"Archivo convertido exitosamente: {output_file}"
            print(success_message)
            # Limpiar archivo de entrada original después de una conversión exitosa
            try:
                os.remove(input_file)
                print(f"Archivo de entrada eliminado: {input_file}")
            except OSError as e:
                print(f"Advertencia: No se pudo eliminar el archivo de entrada {input_file}: {e}")
            return True, output_file

    except ffmpeg.Error as e:
        # Error específico de ffmpeg-python (e.g., al compilar)
        stderr_decoded = e.stderr.decode('utf-8', errors='ignore').strip() if e.stderr else "No stderr available"
        print(f"Error de ffmpeg-python: {stderr_decoded}")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except OSError as e_rm:
                 print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e_rm}")
        return False, f"Error en FFmpeg (compile/setup): {stderr_decoded}"
    except Exception as e:
        # Otros errores inesperados
        error_msg = f"Error inesperado durante la conversión: {str(e)}"
        print(error_msg)
        if os.path.exists(output_file):
           try:
               os.remove(output_file)
           except OSError as e_rm:
                print(f"No se pudo eliminar el archivo de salida fallido {output_file}: {e_rm}")
        return False, error_msg