const $ = s => document.querySelector(s);
const filesInput = $('#files');
const selectedGrid = $('#selectedGrid');
const qualitySlider = $('#qualitySlider');
const qualityValue = $('#qualityValue');
const downloadedSet = new Set();

/* Eventos UI ---------*/
// Actualizamos el valor mostrado cuando el usuario mueve el deslizador de calidad
qualitySlider.addEventListener('input', () => {
    qualityValue.textContent = qualitySlider.value;
});

filesInput.addEventListener('change', updateFormatOptions);

document.getElementById('dropArea').addEventListener('click', () => filesInput.click());
['dragenter','dragover'].forEach(ev => $('#dropArea').addEventListener(ev, e => { e.preventDefault(); $('#dropArea').classList.add('dragover'); }));
['dragleave','drop'].forEach(ev => $('#dropArea').addEventListener(ev, e => { e.preventDefault(); $('#dropArea').classList.remove('dragover'); }));
$('#dropArea').addEventListener('drop', e => {
    const dt = new DataTransfer();
    [...e.dataTransfer.files].forEach(f => dt.items.add(f));
    filesInput.files = dt.files;
    updateFormatOptions();
});

/* Renderizado de miniaturas ----------*/
function renderSelectedPreviews() {
    selectedGrid.innerHTML = '';
    [...filesInput.files].forEach(file => {
        const wrapper = document.createElement('div');
        wrapper.className = 'preview-item';

        const url = URL.createObjectURL(file);
        const isVideo = file.type.startsWith('video');

        let mediaEl;
        if (isVideo) {
            mediaEl = document.createElement('video');
            mediaEl.muted = true;
            mediaEl.autoplay = true;
            mediaEl.loop = true;
        } else{
            const isAudio = file.type.startsWith('audio');
            if (isAudio) {
                mediaEl = document.createElement('audio');
                mediaEl.controls = true;
            } else{
                mediaEl = document.createElement('img');
                mediaEl.alt = 'preview';
            }
        }
        mediaEl.src = url;

        const revoke = () => URL.revokeObjectURL(url);
        if (isVideo) {
            mediaEl.addEventListener('loadeddata', revoke, { once: true });
        } else {
            mediaEl.addEventListener('load', revoke, { once: true });
        }

        const btn = document.createElement('button');
        btn.className = 'remove-btn';
        btn.innerHTML = '&times;';
        btn.dataset.name = file.name;
        btn.addEventListener('click', () => removeFile(file.name));

        wrapper.appendChild(btn);
        wrapper.appendChild(mediaEl);
        selectedGrid.appendChild(wrapper);
    });
}

/* Manejo de archivos seleccionados ------------------*/
function removeFile(name) {
    const dt = new DataTransfer();
    [...filesInput.files].forEach(f => {
        if (f.name !== name) dt.items.add(f);
    });
    filesInput.files = dt.files;
    updateFormatOptions();
}

/* Actualización de opciones de formato ------------------*/
function updateFormatOptions() {
    const select = $('#target_format');
    select.innerHTML = '';
    if (!filesInput.files.length) {
        select.innerHTML = '<option value="">Selecciona un archivo primero</option>';
    } else {
        const first = filesInput.files[0];
        let formats;
        if(first.type.startsWith('video')) formats = ['mp4','avi','mkv','mov','wmv','flv','webm'];
        else{
            if(first.type.startsWith('audio')) formats = ['mp3','m4a','flac','ogg','opus','wav','wma','aac'];
            else formats = ['jpg','jpeg','png','webp','gif','bmp'];
        }
        select.innerHTML = formats.map(f => `<option value="${f}">${f.toUpperCase()}</option>`).join('');
    }
    renderSelectedPreviews();
}

/* Conversión --------------*/
$('#btnConvert').addEventListener('click', async () => {
    if (!filesInput.files.length) return alert('Selecciona al menos un archivo.');

    const format = $('#target_format').value;
    if (!format) return alert('Selecciona el formato de salida.');

    document.getElementById('conversionContainer').classList.add('active');

    const fd = new FormData();
    [...filesInput.files].forEach(f => fd.append('files', f));
    fd.append('target_format', format);
    fd.append('quality_level', qualitySlider.value);

    $('#progressArea').innerHTML = `<div class="progress" role="progressbar"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:0%"></div></div>`;
    previewGrid.innerHTML = '';

    try {
        const res = await fetch('/convert', { method: 'POST', body: fd });
        const { tasks } = await res.json();
        tasks.forEach(task => createTaskCard(task));
    } catch (err) {
        $('#progressArea').innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
});

/* Creación de tarjetas de tareas ------------------*/
function createTaskCard({ task_id, input_file, output_file }) {
    const col = document.createElement('div');
    col.className = 'col-sm-6 col-lg-4'; col.id = `card-${task_id}`;
    col.innerHTML = `
         <div class="card h-100 shadow-sm">
           <div class="card-body">
             <h5 class="card-title">${input_file}</h5>
             <p class="text-muted small mb-3">${output_file}</p>
              <div class="status-badge-container">
               <span class="status-badge processing">Procesando…</span>
              </div>
           </div>
         </div>
       `;
    $('#previewGrid').appendChild(col);
    pollStatus(task_id, output_file);
}

/*  Descarga automática  -------------------------------------*/
function triggerDownload(name) {
    if (downloadedSet.has(name)) return; // Evitar duplicados
    downloadedSet.add(name);

    const link = document.createElement('a');
    link.href = `/download/${encodeURIComponent(name)}`;
    link.download = name;          // Sugerir nombre al navegador
    link.style.display = 'none';   // Ocultar visualmente
    document.body.appendChild(link);

    // Lanzamos la descarga (algunos navegadores bloquean si no hay
    // gesto del usuario; al estar dentro del flujo iniciado por un
    // click explícito, suele permitirse)
    link.click();
    link.remove();
}

/* Polling del estado de cada tarea --------------------------*/
async function pollStatus(id, filename) {
    try {
        const res = await fetch(`/task_status/${id}`);
        const { status, success } = await res.json();
        const badge = document.querySelector(`#card-${id} .status-badge`);

        if (status === 'running') {
            badge.style.width = badge.style.width || '0%';
            badge.parentElement.previousElementSibling.querySelector('.progress-bar').style.width = '50%';
            setTimeout(() => pollStatus(id, filename), 2000);
        } else if (status === 'done' && success) {
            badge.className = 'status-badge completed';
            badge.textContent = 'Completado';
            showPreview(filename, id);
            triggerDownload(filename);
        } else {
            badge.className = 'badge text-bg-danger';
            badge.textContent = 'Error';
        }
    } catch (err) {
        setTimeout(() => pollStatus(id, filename), 4000);
    }
}

/* Vista previa ------------*/
function showPreview(name, id) {
    const ext = name.split('.').pop().toLowerCase();
    const src = `/converted/${encodeURIComponent(name)}`;
    const container = document.querySelector(`#card-${id} .card`);

    const videoExts = ['mp4', 'webm', 'mov', 'mkv', 'avi'];
    const audioExts = ['mp3', 'flac', 'wav', 'ogg', 'opus', 'm4a', 'aac', 'wma'];

    let mediaHtml;
    if (videoExts.includes(ext)) {
        // Vista previa de vídeo
        mediaHtml = `
            <video 
                class="w-100 mt-3 rounded"
                src="${src}"
                controls
                preload="metadata"
                poster="/static/video_placeholder.png"
                style="max-height:240px;"
            >
                Tu navegador no soporta el elemento <code>video</code>.
            </video>
        `;
    } else if (audioExts.includes(ext)) {
        // Vista previa de audio
        mediaHtml = `
            <audio 
                class="w-100 mt-3 rounded"
                src="${src}"
                controls
                preload="auto"
                title="Previsualización de audio"
                style="width:100%;"
            >
                Tu navegador no soporta el elemento <code>audio</code>.
            </audio>
        `;
    } else {
        // Vista previa de imagen
        mediaHtml = `
            <img 
                class="w-100 mt-3 rounded"
                src="${src}"
                alt="Vista previa"
                style="object-fit:contain;max-height:240px;"
            />
        `;
    }

    container.insertAdjacentHTML('beforeend', mediaHtml);
}