const $ = s => document.querySelector(s);
const filesInput = $('#files');
const selectedGrid = $('#selectedGrid');
const qualitySlider = $('#qualitySlider');
const qualityValue = $('#qualityValue');

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
        } else {
            mediaEl = document.createElement('img');
            mediaEl.alt = 'preview';
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

function removeFile(name) {
    const dt = new DataTransfer();
    [...filesInput.files].forEach(f => {
        if (f.name !== name) dt.items.add(f);
    });
    filesInput.files = dt.files;
    updateFormatOptions();
}

function updateFormatOptions() {
    const select = $('#target_format');
    select.innerHTML = '';
    if (!filesInput.files.length) {
        select.innerHTML = '<option value="">Selecciona un archivo primero</option>';
    } else {
        const first = filesInput.files[0];
        const formats = first.type.startsWith('video') ? ['mp4','avi','mkv','mov','wmv','flv','webm'] : ['jpg','jpeg','png','webp','gif','bmp'];
        select.innerHTML = formats.map(f => `<option value="${f}">${f.toUpperCase()}</option>`).join('');
    }
    renderSelectedPreviews();
}

// Conversión y polling
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
        } else {
            badge.className = 'badge text-bg-danger';
            badge.textContent = 'Error';
        }
    } catch (err) {
        setTimeout(() => pollStatus(id, filename), 4000);
    }
}

function showPreview(name, id) {
    const ext = name.split('.').pop().toLowerCase();
    const src = `/converted/${encodeURIComponent(name)}`;
    const container = document.querySelector(`#card-${id} .card`);
    const mediaHtml = ['mp4','webm','mov','mkv','avi'].includes(ext)
        ? `<video class=\"w-100 mt-3 rounded\" controls src=\"${src}\"></video>`
        : `<img class=\"w-100 mt-3 rounded\" src=\"${src}\" alt=\"preview\" />`;
    container.insertAdjacentHTML('beforeend', mediaHtml);
}