let currentPath = '';
let editorPath = '';

// ── File Browser ────────────────────────────────

async function loadFiles(path) {
    if (path !== undefined) currentPath = path;
    const body = document.getElementById('files-body');

    try {
        const url = '/api/files' + (currentPath ? '?path=' + encodeURIComponent(currentPath) : '');
        const resp = await fetch(url);
        if (!resp.ok) {
            const err = await resp.json();
            body.innerHTML = `<tr><td colspan="5" style="color:var(--red)">${escapeHtml(err.detail || 'Error')}</td></tr>`;
            return;
        }
        const data = await resp.json();
        currentPath = data.path;
        renderBreadcrumb(currentPath);

        if (data.files.length === 0) {
            body.innerHTML = '<tr><td colspan="5" style="color:var(--text-dim)">Empty directory</td></tr>';
            return;
        }

        body.innerHTML = data.files.map(f => {
            const icon = f.is_dir ? '&#128193;' : '&#128196;';
            const size = f.is_dir ? '—' : formatBytes(f.size);
            const nameHtml = f.is_dir
                ? `<span class="file-icon">${icon}</span><span class="file-name-link" onclick="loadFiles('${escapeAttr(f.path)}')">${escapeHtml(f.name)}</span>`
                : `<span class="file-icon">${icon}</span><span class="file-name-link" onclick="editFile('${escapeAttr(f.path)}')">${escapeHtml(f.name)}</span>`;

            return `
                <tr>
                    <td>${nameHtml}</td>
                    <td style="color:var(--text-dim);font-size:13px">${size}</td>
                    <td style="color:var(--text-dim);font-size:13px;font-family:monospace">${f.permissions}</td>
                    <td style="color:var(--text-dim);font-size:13px">${f.modified}</td>
                    <td>
                        <div class="btn-group">
                            ${!f.is_dir ? `
                                <button class="btn btn-small" onclick="downloadFile('${escapeAttr(f.path)}')">Download</button>
                                <button class="btn btn-small btn-danger" onclick="deleteFile('${escapeAttr(f.path)}','${escapeAttr(f.name)}')">Delete</button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        body.innerHTML = `<tr><td colspan="5" style="color:var(--red)">Failed to load files</td></tr>`;
    }
}

function escapeAttr(s) {
    return s.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// ── Breadcrumb ──────────────────────────────────

function renderBreadcrumb(path) {
    const el = document.getElementById('breadcrumb');
    const parts = path.split('/').filter(Boolean);
    let html = '<span class="breadcrumb-item" onclick="loadFiles(\'/\')">/ root</span>';
    let built = '';
    for (const part of parts) {
        built += '/' + part;
        const p = built;
        html += `<span class="breadcrumb-sep">/</span>
                 <span class="breadcrumb-item" onclick="loadFiles('${escapeAttr(p)}')">${escapeHtml(part)}</span>`;
    }
    el.innerHTML = html;
}

// ── File Actions ────────────────────────────────

function downloadFile(path) {
    window.open('/api/files/download?path=' + encodeURIComponent(path), '_blank');
}

async function deleteFile(path, name) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
        const resp = await fetch('/api/files?path=' + encodeURIComponent(path), { method: 'DELETE' });
        if (resp.ok) {
            loadFiles();
        } else {
            const err = await resp.json();
            alert(err.detail || 'Delete failed');
        }
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}

// ── Editor ──────────────────────────────────────

async function editFile(path) {
    editorPath = path;
    const modal = document.getElementById('editor-modal');
    const title = document.getElementById('editor-title');
    const content = document.getElementById('editor-content');

    title.textContent = path.split('/').pop();
    content.value = 'Loading...';
    modal.classList.add('active');

    try {
        const resp = await fetch('/api/files/read?path=' + encodeURIComponent(path));
        if (!resp.ok) {
            const err = await resp.json();
            content.value = 'Error: ' + (err.detail || 'Failed to read file');
            return;
        }
        const data = await resp.json();
        content.value = data.content;
    } catch (e) {
        content.value = 'Error: ' + e.message;
    }
}

async function saveFile() {
    const content = document.getElementById('editor-content').value;
    try {
        const resp = await fetch('/api/files/write', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: editorPath, content }),
        });
        if (resp.ok) {
            closeEditor();
            loadFiles();
        } else {
            const err = await resp.json();
            alert(err.detail || 'Save failed');
        }
    } catch (e) {
        alert('Save failed: ' + e.message);
    }
}

function closeEditor() {
    document.getElementById('editor-modal').classList.remove('active');
    editorPath = '';
}

// ── Upload ──────────────────────────────────────

function initUpload() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('upload-input');
    const toggleBtn = document.getElementById('upload-toggle-btn');

    toggleBtn.addEventListener('click', () => {
        zone.classList.toggle('active');
    });

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        uploadFiles(e.dataTransfer.files);
    });

    input.addEventListener('change', () => {
        uploadFiles(input.files);
        input.value = '';
    });
}

async function uploadFiles(fileList) {
    for (const file of fileList) {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch('/api/files/upload?destination=' + encodeURIComponent(currentPath), {
                method: 'POST',
                body: formData,
            });
            if (!resp.ok) {
                const err = await resp.json();
                alert(`Upload "${file.name}" failed: ${err.detail || 'Error'}`);
            }
        } catch (e) {
            alert(`Upload "${file.name}" failed: ${e.message}`);
        }
    }
    loadFiles();
    document.getElementById('upload-zone').classList.remove('active');
}

// ── New Folder ──────────────────────────────────

function initMkdir() {
    document.getElementById('mkdir-btn').addEventListener('click', async () => {
        const name = prompt('New folder name:');
        if (!name) return;
        const path = currentPath.replace(/\/$/, '') + '/' + name;
        try {
            const resp = await fetch('/api/files/mkdir?path=' + encodeURIComponent(path), {
                method: 'POST',
            });
            if (resp.ok) {
                loadFiles();
            } else {
                const err = await resp.json();
                alert(err.detail || 'Failed to create folder');
            }
        } catch (e) {
            alert('Failed: ' + e.message);
        }
    });
}

// ── Init ────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initMkdir();

    document.getElementById('editor-close').addEventListener('click', closeEditor);
    document.getElementById('editor-cancel').addEventListener('click', closeEditor);
    document.getElementById('editor-save').addEventListener('click', saveFile);
    document.getElementById('refresh-files-btn').addEventListener('click', () => loadFiles());

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeEditor();
    });
});
