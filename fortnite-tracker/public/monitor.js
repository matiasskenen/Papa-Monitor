/* ===== monitor.js – lógica del panel público ===== */
const API_BASE = "";
const OPT_ES = { timeZone: 'Europe/Madrid', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' };
const OPT_AR = { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit' };
let detailChart = null;

// ── helpers ──
function fmt(iso, opts) {
    if (!iso) return '—';
    const d = new Date(iso);
    return isNaN(d.getTime()) ? '—' : new Intl.DateTimeFormat('es-ES', opts).format(d);
}

function getDur(start, end, active) {
    const a = new Date(start);
    const b = active ? new Date() : (end ? new Date(end) : null);
    if (!b || isNaN(a.getTime())) return '—';
    const mins = Math.max(0, Math.floor((b - a) / 60000));
    return Math.floor(mins / 60) + 'h ' + (mins % 60) + 'm';
}

function getUrl(path) {
    if (!API_BASE && path.startsWith('/')) {
        return window.location.origin.startsWith('http') ? path : null;
    }
    return API_BASE + path;
}

// ── navegación ──
function showSection(id, btn) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    btn.classList.add('active');
    if (id === 'graficos') loadGraficos();
    window.scrollTo(0, 0);
}

// ── relojes ──
function updateClocks() {
    const opt = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
    try {
        document.getElementById('clock-es').textContent =
            new Intl.DateTimeFormat('es-ES', { ...opt, timeZone: 'Europe/Madrid' }).format(new Date());
        document.getElementById('clock-ar').textContent =
            new Intl.DateTimeFormat('es-ES', { ...opt, timeZone: 'America/Argentina/Buenos_Aires' }).format(new Date());
    } catch(e) {}
}

// ── estado actual + últimas sesiones ──
async function loadData() {
    let sessions = [];
    const url = getUrl('/api/status');
    if (url) {
        try {
            const res = await fetch(url);
            if (res.ok) { const d = await res.json(); if (Array.isArray(d)) sessions = d; }
        } catch(e) { console.warn('API no disponible'); }
    }

    const list = document.getElementById('last-sessions-list');
    if (!sessions.length) { list.innerHTML = '<li>Sin actividad reciente</li>'; return; }

    list.innerHTML = sessions.slice(0, 3).map((s, i) => `
        <li>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <b style="font-size:0.7rem;color:var(--fn-blue)">SESIÓN ${i+1}</b>
                <span style="font-size:0.6rem;padding:2px 6px;border-radius:4px;background:${s.is_active?'var(--fn-purple)':'#333'}">
                    ${s.is_active ? 'EN CURSO' : 'FINALIZADA'}
                </span>
            </div>
            <div style="font-size:0.85rem">
                <div>🇪🇸 ${fmt(s.start_time, OPT_ES)}</div>
                <div style="color:var(--fn-yellow);margin-top:4px">Duración: ${getDur(s.start_time, s.end_time, s.is_active)}</div>
            </div>
        </li>`).join('');

    const top = sessions[0];
    const st  = document.getElementById('status-text');
    const pt  = document.getElementById('play-time');
    const hi  = document.getElementById('offline-hint');

    if (top.is_active) {
        st.textContent = 'ONLINE';  st.className = 'status-badge online';
        pt.textContent = 'Jugando ahora mismo';
        hi.style.display = 'none';
    } else {
        st.textContent = 'OFFLINE'; st.className = 'status-badge offline';
        pt.textContent = 'Desconectado';
        if (top.end_time) { hi.style.display = 'block'; hi.textContent = 'Última vez: ' + fmt(top.end_time, OPT_ES); }
    }
}

// ── gráficos ──
async function loadGraficos() {
    // --- Gráfico de minutos por día ---
    let byDay = [];
    const url = getUrl('/api/stats/playtime?days=30&tz=America/Argentina/Buenos_Aires');
    if (url) {
        try {
            const res = await fetch(url);
            if (res.ok) { const d = await res.json(); byDay = d.by_day || []; }
        } catch(e) { console.warn('API stats no disponible'); }
    }

    const ctx = document.getElementById('playtimeChart').getContext('2d');
    if (detailChart) detailChart.destroy();
    detailChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: byDay.map(x => x.date.slice(5)), // MM-DD
            datasets: [{
                label: 'Minutos jugados',
                data: byDay.map(x => Math.round(x.minutes)),
                backgroundColor: 'rgba(167,34,255,0.6)',
                borderColor: '#a722ff',
                borderRadius: 6,
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const m = ctx.parsed.y;
                            return `${Math.floor(m/60)}h ${m%60}m`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#888', callback: v => Math.floor(v/60)+'h' }
                },
                x: { grid: { display: false }, ticks: { color: '#888', maxRotation: 45 } }
            }
        }
    });

    // --- Tabla de sesiones recientes ---
    let sessions = [];
    const sUrl = getUrl('/api/status?limit=30');
    if (sUrl) {
        try {
            const res = await fetch(sUrl);
            if (res.ok) { const d = await res.json(); if (Array.isArray(d)) sessions = d; }
        } catch(e) {}
    }

    const tbody = document.querySelector('#sessions-table tbody');
    tbody.innerHTML = sessions.map(s => `
        <tr>
            <td>${fmt(s.start_time, OPT_ES)}</td>
            <td>${s.is_active ? '—' : fmt(s.end_time, OPT_ES)}</td>
            <td>${getDur(s.start_time, s.end_time, s.is_active)}</td>
            <td><span style="color:${s.is_active?'#00ff88':'#888'}">${s.is_active?'Activa':'Cerrada'}</span></td>
        </tr>`).join('') || `<tr><td colspan="4" style="text-align:center;color:#555">Sin sesiones registradas</td></tr>`;
}

// ── init ──
updateClocks();
loadData();
setInterval(updateClocks, 1000);
setInterval(loadData, 20000);
