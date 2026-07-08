const App = {
    hostname: '',
    vpsStatus: 'disconnected',
    dashboardWs: null,
    chatWs: null,
    wsRetryDelay: 1000,
    wsMaxRetry: 30000,
};

// ── Init ────────────────────────────────────────

async function initApp() {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    App.hostname = data.hostname;
    document.getElementById('hostname-display').textContent = data.hostname;
    updateVpsStatus(data.vps_status);

    initTabs();
    connectDashboardWs();
    connectChatWs();
    loadDashboard();
    loadFiles();
    loadMessages();
    loadPeers();
}

// ── Tabs ────────────────────────────────────────

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });
}

// ── VPS Status ──────────────────────────────────

function updateVpsStatus(status) {
    App.vpsStatus = status;
    const dot = document.getElementById('vps-dot');
    const text = document.getElementById('vps-status-text');
    dot.className = 'status-dot ' + status;
    const labels = {
        connected: 'VPS Connected',
        connecting: 'Connecting...',
        disconnected: 'VPS Disconnected',
    };
    text.textContent = labels[status] || status;
}

// ── Dashboard WebSocket ─────────────────────────

function connectDashboardWs() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    App.dashboardWs = new WebSocket(`${proto}//${location.host}/ws/dashboard`);
    let retryDelay = App.wsRetryDelay;

    App.dashboardWs.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'vps_status') {
            updateVpsStatus(data.status);
        } else if (data.type === 'metrics') {
            updateMetrics(data);
        } else if (data.type === 'peers') {
            renderPeers(data.peers);
        }
    };

    App.dashboardWs.onclose = () => {
        setTimeout(() => {
            retryDelay = Math.min(retryDelay * 2, App.wsMaxRetry);
            connectDashboardWs();
        }, retryDelay);
    };

    App.dashboardWs.onopen = () => { retryDelay = App.wsRetryDelay; };
}

// ── Chat WebSocket ──────────────────────────────

function connectChatWs() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    App.chatWs = new WebSocket(`${proto}//${location.host}/ws/chat`);
    let retryDelay = App.wsRetryDelay;

    App.chatWs.onopen = () => {
        retryDelay = App.wsRetryDelay;
        App.chatWs.send(JSON.stringify({ type: 'join', hostname: App.hostname }));
    };

    App.chatWs.onmessage = (e) => {
        const data = JSON.parse(e.data);
        appendChatMessage(data);
    };

    App.chatWs.onclose = () => {
        setTimeout(() => {
            retryDelay = Math.min(retryDelay * 2, App.wsMaxRetry);
            connectChatWs();
        }, retryDelay);
    };
}

// ── Helpers ─────────────────────────────────────

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', initApp);
