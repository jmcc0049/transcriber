# Transcriber – Conversor multimedia por lotes

Transcriber es una herramienta web (SPA) que convierte lotes de vídeo, audio e imagen entre los formatos más habituales sin bloquear la interfaz gráfica.  
Su núcleo está escrito en **Python 3 + Flask** y delega la codificación a **FFmpeg**; el front-end es una aplicación de página única (HTML + Vanilla JS + Bootstrap 5).

---
![Captura de pantalla](static/screenshot.jpg)
---

## 🚀 Motivación y decisiones de diseño

| Requisito | Decisión | Ventajas |
|-----------|----------|----------|
| Conversión multi-formato, con control de calidad | **FFmpeg** a través de la librería *ffmpeg-python* | Soporta prácticamente cualquier códec / contenedor y permite un mapeo expresivo de parámetros. |
| Operaciones en 2.º plano | `concurrent.futures.ThreadPoolExecutor` con tantos workers como CPUs disponibles | La UI nunca se bloquea y el rendimiento escala al hardware. |
| Interfaz moderna y UX fluida | **SPA** + Bootstrap 5 + Fetch API + miniaturas en vivo | Feedback inmediato, arrastrar/soltar y vistas previas automáticas. |
| Portabilidad | **Python 3.10+** y dependencias mínimas del sistema (Ubuntu LTS) | Fácil de desplegar en servidores comunes o contenedores. |
| Conversión por perfiles | Deslizador *Quality Level* 1-100 → parámetros CRF/bitrate en `logic.py` | Unifica la experiencia para vídeo, audio e imágenes. |
Privacidad | Procesamiento 100 % local con FFmpeg en la propia máquina/servidor | Ningún archivo sale de tu red; no se cargan metadatos en servicios externos; cumplimiento sencillo de GDPR. 


## 🏗️ Arquitectura

SPA (HTML/JS) ───── fetch /convert ─────┐

│

Flask (WSGI) ➜ ThreadPool ➜ convert_file() ➜ FFmpeg

│

SPA ← poll /task_status <id> ←─────────┘


- **Front-end** (static/)  
  HTML5, Bootstrap 5, íconos de *bootstrap-icons* y un único `app.js` que:
  1. Gestiona la lista de archivos,
  2. Lanza la petición `/convert`,
  3. Hace *polling* al estado y muestra miniaturas o reproductores nativos.

- **Back-end** (`app.py`)  
  API REST en Flask. Cada archivo se encola en un *future*, aprovechando al máximo las capacidades del host.

- **Conversión** (`logic.py`)  
  Genera dinámicamente la línea de comandos de FFmpeg (o `heif-convert` para HEIC) y limpia los temporales.

## ⚠️ Excepciones/Casos Especiales en la conversión
Aunque la conversión multi-formato se resuelve de manera general con FFmpeg, algunos formatos requieren un tratamiento especial por sus particularidades técnicas:

  1. Formatos de imagen HEIF/HEIC (Procesamiento en bloques 512x512):
  Las imágenes HEIF/HEIC pueden estar codificadas internamente en bloques de 512x512 píxeles, lo que puede llevar a que, tras una conversión directa, sólo se obtenga una parte de la imagen original o una resolución limitada si no se maneja correctamente.
  Conversión auxiliar: Para asegurar una conversión fiable, se realiza primero una conversión intermedia a PNG mediante la utilidad heif-convert antes de pasar el archivo a FFmpeg. Esto garantiza la extracción completa de la imagen, independientemente de cómo esté segmentada internamente.

  2. Formatos de vídeo WebM y WMV (Restricción de códecs de audio):
  El contenedor WebM, por estándar, solo admite ciertos formatos de audio (principalmente Opus y Vorbis). Intentar multiplexar audio en formatos como AAC o MP3 dentro de un WebM produce errores de incompatibilidad o archivos corruptos.
  Selección automática de códec: El backend detecta cuando la salida es WebM y ajusta automáticamente el códec de audio a uno compatible (usualmente Opus), aunque el usuario haya seleccionado otra preferencia, para asegurar la interoperabilidad y reproducción correcta en navegadores modernos.

  3. Limitaciones en vistas previas:
  La previsualización automática sólo es posible en aquellos formatos soportados por el navegador del usuario (por ejemplo, MP4/H.264/AAC y WebM/VP9/Opus). Otros formatos menos habituales pueden requerir descarga manual para su reproducción.

  4. Cambios en la lógica del deslizador de calidad:
  Cuando el usuario selecciona un formato de salida sin pérdida (lossless), como WAV o FLAC, el deslizador de calidad deja de controlar el parámetro típico de bitrate o CRF, y pasa a gestionar el ratio de compresión (en el caso de FLAC) o se desactiva (en WAV, ya que no existe compresión).
      - En FLAC, un valor bajo en el deslizador implica una mayor velocidad de codificación y menor compresión, mientras que valores altos implican máxima compresión (pero mayor uso de CPU y menor velocidad).
      - En WAV, la calidad siempre es máxima (sin compresión), por lo que el deslizador queda inutilizado o deshabilitado automáticamente.

## 💡 Lecciones aprendidas

1. **HEIF/HEIC**: Muchos navegadores no soportan vistas previas; se añadió un paso a PNG usando `heif-convert` antes de invocar FFmpeg.  
2. **Seguridad**: Se validan *MIME* y extensión antes de ejecutar FFmpeg para evitar inyección de parámetros.  
3. **Escalabilidad**: Stateless; puede crecer horizontalmente detrás de Nginx con un almacén compartido (por ejemplo, el servicio S3 de AWS).

## ✍️ Experiencia personal
El planteamiento inicial del proyecto fue desarrollarlo completamente en C++, buscando la máxima eficiencia y control sobre los procesos de conversión multimedia. Sin embargo, pronto surgieron varias limitaciones importantes:

- Escasez de frameworks fiables para construir APIs REST: En C/C++, la mayoría de soluciones para exponer una API web son muy básicas o requieren una infraestructura compleja, lo que dificulta construir una interfaz moderna y mantenible.

- Integración poco amigable con FFmpeg: Aunque FFmpeg está escrito en C, la utilización directa de su API resulta poco práctica para aplicaciones web modernas, y su integración con frameworks de C es limitada, especialmente cuando se requieren operaciones asincrónicas y procesamiento en segundo plano.

- Desarrollo y mantenimiento: El desarrollo en C para este tipo de aplicación implica mayor carga de trabajo, especialmente en la gestión de memoria y concurrencia, lo que ralentiza la iteración y aumenta la probabilidad de errores difíciles de depurar.