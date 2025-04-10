import os
import ffmpeg

def convert_file(input_file, output_file, is_video, convesions_folder):
    """
    Realiza la conversión utilizando ffmpeg.
    Para vídeos se aplica un escalado por defecto y para imágenes se realiza una conversión simple.
    """
    stream = ffmpeg.input(input_file)
    if is_video:
        # Ejemplo: aplicar escalado a 1280x720 para vídeos (se puede parametrizar)
        video = stream.video.filter('scale', 1280, 720)
        audio = stream.audio
        output = ffmpeg.output(video, audio, output_file,
                               vcodec='libx264',
                               acodec='aac',
                               video_bitrate='800k',
                               audio_bitrate='128k',
                               format='mp4')
    else:
        # Conversión simple para imágenes
        output = ffmpeg.output(stream, output_file)

    try:
        ffmpeg.run(output, overwrite_output=True, capture_stderr=True, capture_stdout=True)
    except Exception as e:
        print(str(e))

    if os.path.exists(output_file):
        print(f"Archivo convertido generado: {output_file}")
    else:
        print(f"Error: No se generó el archivo convertido: {output_file}")

    # Mover el archivo convertido a la carpeta de conversiones
    converted_path = os.path.join(convesions_folder, os.path.basename(output_file))
    os.rename(output_file, converted_path)
    return True, input_file, output_file