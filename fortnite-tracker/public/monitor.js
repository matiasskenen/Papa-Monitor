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
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return (h > 0 ? h + 'h ' : '') + m + 'm';
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
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('sidebar-item-active', 'text-white');
        b.classList.add('text-slate-400');
        const svg = b.querySelector('svg');
        if (svg) svg.classList.remove('text-indigo-400');
    });

    const target = document.getElementById(id);
    if (target) target.classList.add('active');
    
    btn.classList.add('sidebar-item-active', 'text-white');
    btn.classList.remove('text-slate-400');
    const svg = btn.querySelector('svg');
    if (svg) svg.classList.add('text-indigo-400');

    if (id === 'graficos') loadGraficos();
    window.scrollTo(0, 0);
}

// ── relojes ──
function updateClocks() {
    const opt = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
    try {
        const esClock = document.getElementById('clock-es');
        const arClock = document.getElementById('clock-ar');
        if (esClock) esClock.textContent = new Intl.DateTimeFormat('es-ES', { ...opt, timeZone: 'Europe/Madrid' }).format(new Date());
        if (arClock) arClock.textContent = new Intl.DateTimeFormat('es-ES', { ...opt, timeZone: 'America/Argentina/Buenos_Aires' }).format(new Date());
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
    if (!sessions.length) { 
        list.innerHTML = '<div class="glass p-6 text-center text-slate-500">Sin actividad reciente</div>'; 
    } else {
        list.innerHTML = sessions.slice(0, 3).map((s, i) => `
            <div class="glass p-6 group hover:bg-white/[0.05] transition-all cursor-pointer flex items-center justify-between" onclick="showSection('sesiones', document.querySelectorAll('.nav-btn')[2])">
                <div class="flex items-center gap-6">
                    <div class="w-12 h-12 rounded-2xl ${s.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400'} flex items-center justify-center group-hover:scale-110 transition-transform">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <div>
                        <h4 class="text-lg font-semibold flex items-center gap-3">
                            Sesión #${sessions.length - i}
                            <span class="text-xs font-normal text-slate-500">${fmt(s.start_time, { day: '2-digit', month: 'short' })}</span>
                        </h4>
                        <div class="flex items-center gap-4 mt-1 text-sm">
                            <span class="text-indigo-300 font-medium">${fmt(s.start_time, { hour: '2-digit', minute: '2-digit' })} — ${s.is_active ? 'Ahora' : fmt(s.end_time, { hour: '2-digit', minute: '2-digit' })}</span>
                            <span class="text-slate-500">•</span>
                            <span class="text-emerald-400 font-medium">${getDur(s.start_time, s.end_time, s.is_active)}</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-8">
                    <div class="text-right hidden sm:block">
                        <p class="text-xs text-slate-500 uppercase font-bold tracking-widest">Estado</p>
                        <span class="text-white text-sm">${s.is_active ? 'En curso' : 'Finalizada'}</span>
                    </div>
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-slate-600 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                </div>
            </div>
        `).join('');
    }

    const top = sessions[0];
    if (!top) return;

    const st  = document.getElementById('status-text');
    const pt  = document.getElementById('play-time');
    const card = document.getElementById('status-card');
    const glow = document.getElementById('status-glow');
    const dot  = document.getElementById('status-dot');
    const lastSeen = document.getElementById('last-seen');
    const hi = document.getElementById('offline-hint');
    const hiContainer = document.getElementById('offline-hint-container');

    if (top.is_active) {
        st.textContent = 'ONLINE';
        st.className = "text-7xl font-black mb-4 tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-emerald-400 to-emerald-600";
        card.classList.add('online');
        glow.className = "absolute -top-24 -left-24 w-64 h-64 bg-emerald-500/20 blur-[100px] rounded-full transition-colors duration-1000";
        dot.className = "w-2 h-2 rounded-full bg-emerald-500 pulse-online";
        pt.textContent = '¡El sistema está transmitiendo actividad en tiempo real!';
        if (hiContainer) hiContainer.style.display = 'none';
    } else {
        st.textContent = 'OFFLINE';
        st.className = "text-7xl font-black mb-4 tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40";
        card.classList.remove('online');
        glow.className = "absolute -top-24 -left-24 w-64 h-64 bg-rose-500/20 blur-[100px] rounded-full transition-colors duration-1000";
        dot.className = "w-2 h-2 rounded-full bg-rose-500 pulse-offline";
        pt.textContent = 'El sistema se encuentra desconectado actualmente.';
        if (hiContainer) hiContainer.style.display = 'flex';
        if (top.end_time && hi) hi.textContent = getDur(top.end_time, new Date(), false);
    }

    if (lastSeen) {
        const timeToShow = top.is_active ? top.start_time : top.end_time;
        lastSeen.textContent = fmt(timeToShow, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    }
}

// ── gráficos ──
async function loadGraficos() {
    let byDay = [];
    const url = getUrl('/api/stats/playtime?days=30&tz=America/Argentina/Buenos_Aires');
    if (url) {
        try {
            const res = await fetch(url);
            if (res.ok) { const d = await res.json(); byDay = d.by_day || []; }
        } catch(e) { console.warn('API stats no disponible'); }
    }

    const canvas = document.getElementById('playtimeChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (detailChart) detailChart.destroy();
    detailChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: byDay.map(x => x.date.slice(5)), // MM-DD
            datasets: [{
                label: 'Minutos',
                data: byDay.map(x => Math.round(x.minutes)),
                backgroundColor: 'rgba(99, 102, 241, 0.5)',
                borderColor: '#6366f1',
                borderRadius: 8,
                borderWidth: 1,
                hoverBackgroundColor: 'rgba(99, 102, 241, 0.8)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 13 },
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: ctx => {
                            const m = ctx.parsed.y;
                            return `Jugado: ${Math.floor(m/60)}h ${m%60}m`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
                    ticks: { color: '#64748b', font: { size: 11 }, callback: v => v >= 60 ? Math.floor(v/60)+'h' : v+'m' }
                },
                x: { 
                    grid: { display: false }, 
                    ticks: { color: '#64748b', font: { size: 11 }, maxRotation: 45 } 
                }
            }
        }
    });

    // --- Tabla de sesiones ---
    let sessions = [];
    const sUrl = getUrl('/api/status?limit=30');
    if (sUrl) {
        try {
            const res = await fetch(sUrl);
            if (res.ok) { const d = await res.json(); if (Array.isArray(d)) sessions = d; }
        } catch(e) {}
    }

    const tbody = document.querySelector('#sessions-table tbody');
    if (tbody) {
        tbody.innerHTML = sessions.map(s => `
            <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="font-medium text-slate-300">${fmt(s.start_time, OPT_ES)}</td>
                <td class="text-slate-400">${s.is_active ? '—' : fmt(s.end_time, OPT_ES)}</td>
                <td class="text-indigo-300 font-mono">${getDur(s.start_time, s.end_time, s.is_active)}</td>
                <td>
                    <span class="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${s.is_active?'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20':'bg-slate-500/10 text-slate-400 border border-slate-500/20'}">
                        ${s.is_active?'Activa':'Cerrada'}
                    </span>
                </td>
            </tr>`).join('') || `<tr><td colspan="4" class="text-center py-10 text-slate-500">Sin sesiones registradas</td></tr>`;
    }
}

// ── init ──
window.addEventListener('DOMContentLoaded', () => {
    updateClocks();
    loadData();
    setInterval(updateClocks, 1000);
    setInterval(loadData, 20000);
});
