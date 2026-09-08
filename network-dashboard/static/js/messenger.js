// ── Chat Messages ───────────────────────────────

async function loadMessages() {
    try {
        const resp = await fetch('/api/messages?limit=100');
        const data = await resp.json();
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        data.messages.forEach(msg => appendChatMessage({ type: 'message', ...msg }));
    } catch {}
}

function appendChatMessage(data) {
    const container = document.getElementById('chat-messages');

    if (data.type === 'system') {
        const el = document.createElement('div');
        el.className = 'chat-msg system';
        el.textContent = data.content;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
        return;
    }

    if (data.type !== 'message') return;

    const isSelf = data.sender === App.hostname;
    const el = document.createElement('div');
    el.className = 'chat-msg ' + (isSelf ? 'self' : 'other');

    const sender = document.createElement('div');
    sender.className = 'chat-msg-sender';
    sender.textContent = data.sender;

    const content = document.createElement('div');
    content.textContent = data.content;

    const time = document.createElement('div');
    time.className = 'chat-msg-time';
    time.textContent = formatTime(data.timestamp);

    el.appendChild(sender);
    el.appendChild(content);
    el.appendChild(time);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function formatTime(ts) {
    if (!ts) return '';
    try {
        const d = new Date(ts + (ts.includes('Z') || ts.includes('+') ? '' : 'Z'));
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return ts;
    }
}

// ── Chat Peers Sidebar ─────────────────────────

function renderChatPeers(peers) {
    const el = document.getElementById('chat-peers');
    if (!peers || peers.length === 0) {
        el.innerHTML = '<div style="color:var(--text-dim);font-size:13px">No peers</div>';
        return;
    }
    el.innerHTML = peers.map(p => `
        <div class="peer-item">
            <span class="peer-dot ${p.status}"></span>
            <span>${escapeHtml(p.hostname)}</span>
        </div>
    `).join('');
}

// ── Send Message ────────────────────────────────

function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (!content || !App.chatWs || App.chatWs.readyState !== WebSocket.OPEN) return;

    App.chatWs.send(JSON.stringify({ type: 'message', content }));
    input.value = '';
    input.focus();
}

// ── Init ────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('chat-send').addEventListener('click', sendMessage);

    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
