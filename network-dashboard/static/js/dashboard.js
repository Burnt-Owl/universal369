// ── Metrics ─────────────────────────────────────

function updateMetrics(data) {
    document.getElementById('metric-cpu').textContent = data.cpu.toFixed(1) + '%';
    document.getElementById('metric-load').textContent = 'Load: ' + data.load;

    const memPct = data.mem_total_mb > 0
        ? ((data.mem_used_mb / data.mem_total_mb) * 100).toFixed(0) + '%'
        : '—';
    document.getElementById('metric-mem').textContent = memPct;
    document.getElementById('metric-mem-detail').textContent =
        data.mem_used_mb + ' / ' + data.mem_total_mb + ' MB';

    document.getElementById('metric-disk').textContent = data.disk_used;
    document.getElementById('metric-disk-detail').textContent = 'of ' + data.disk_total;

    document.getElementById('metric-uptime').textContent = data.uptime;
}

// ── Services ────────────────────────────────────

async function loadServices() {
    const body = document.getElementById('services-body');
    try {
        const resp = await fetch('/api/services');
        if (!resp.ok) {
            body.innerHTML = '<tr><td colspan="3" style="color:var(--text-dim)">VPS not connected</td></tr>';
            return;
        }
        const data = await resp.json();
        if (data.services.length === 0) {
            body.innerHTML = '<tr><td colspan="3" style="color:var(--text-dim)">No managed services found</td></tr>';
            return;
        }
        body.innerHTML = data.services.map(svc => `
            <tr>
                <td>${escapeHtml(svc.name)}</td>
                <td><span class="badge badge-${svc.status === 'running' ? 'active' : 'inactive'}">${svc.status}</span></td>
                <td>
                    <div class="btn-group">
                        ${svc.status === 'running'
                            ? `<button class="btn btn-small" onclick="serviceAction('${svc.name}','restart')">Restart</button>
                               <button class="btn btn-small btn-danger" onclick="serviceAction('${svc.name}','stop')">Stop</button>`
                            : `<button class="btn btn-small" onclick="serviceAction('${svc.name}','start')">Start</button>`
                        }
                    </div>
                </td>
            </tr>
        `).join('');
    } catch {
        body.innerHTML = '<tr><td colspan="3" style="color:var(--red)">Failed to load services</td></tr>';
    }
}

async function serviceAction(name, action) {
    if (action === 'stop' && !confirm(`Stop service "${name}"?`)) return;
    try {
        const resp = await fetch(`/api/services/${name}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action }),
        });
        const data = await resp.json();
        if (!resp.ok) alert(data.detail || 'Action failed');
        setTimeout(loadServices, 1000);
    } catch (e) {
        alert('Service action failed: ' + e.message);
    }
}

// ── Peers ───────────────────────────────────────

function renderPeers(peers) {
    const body = document.getElementById('peers-body');
    const count = document.getElementById('peer-count');
    const online = peers.filter(p => p.status === 'online').length;
    count.textContent = online + ' peer' + (online !== 1 ? 's' : '') + ' online';

    if (peers.length === 0) {
        body.innerHTML = '<tr><td colspan="4" style="color:var(--text-dim)">No peers registered</td></tr>';
        return;
    }
    body.innerHTML = peers.map(p => `
        <tr>
            <td>${escapeHtml(p.hostname)}</td>
            <td style="color:var(--text-dim);font-size:13px">${escapeHtml(p.address)}</td>
            <td><span class="badge badge-${p.status}">${p.status}</span></td>
            <td style="color:var(--text-dim);font-size:13px">${p.last_seen || '—'}</td>
        </tr>
    `).join('');

    renderChatPeers(peers);
}

async function loadPeers() {
    try {
        const resp = await fetch('/api/peers');
        const data = await resp.json();
        renderPeers(data.peers);
    } catch {}
}

// ── Connection Log ──────────────────────────────

async function loadConnectionLog() {
    const el = document.getElementById('connection-log');
    try {
        const resp = await fetch('/api/connection-log');
        const data = await resp.json();
        if (data.logs.length === 0) {
            el.textContent = 'No connection events yet';
            return;
        }
        el.innerHTML = data.logs.map(log => `
            <div>
                <span class="log-entry-time">${log.timestamp}</span>
                <span class="log-entry-target">${escapeHtml(log.target)}</span>
                <span class="log-entry-event">${escapeHtml(log.event)}</span>
            </div>
        `).join('');
        el.scrollTop = el.scrollHeight;
    } catch {
        el.textContent = 'Failed to load log';
    }
}

// ── Load All ────────────────────────────────────

function loadDashboard() {
    loadServices();
    loadConnectionLog();
    setInterval(loadServices, 30000);
    setInterval(loadConnectionLog, 15000);
}
