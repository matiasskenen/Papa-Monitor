/* ===== index.js – lógica del sitio público principal ===== */
const OPT_ES = { timeZone: 'Europe/Madrid', dateStyle: 'short', timeStyle: 'short' };

function fmtZone(iso, opts) {
    if (!iso) return '—';
    const d = new Date(iso);
    return isNaN(d.getTime()) ? '—' : new Intl.DateTimeFormat('es-ES', opts).format(d);
}

async function loadHomeSessions() {
    const tbody = document.querySelector('#home-sessions tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#555">Cargando...</td></tr>';
    try {
        const res = await fetch('/api/status?limit=10');
        const data = await res.json();
        if (!Array.isArray(data) || !data.length) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#555">Sin sesiones</td></tr>';
            return;
        }
        tbody.innerHTML = data.slice(0, 3).map((s, i) => {
            const st = s.is_active ? 'Activa' : 'Cerrada';
            return `<tr>
                <td>${i + 1}</td>
                <td><span style="color:${s.is_active?'#00ff88':'#888'}">${st}</span></td>
                <td class="mono-time">${fmtZone(s.start_time, OPT_ES)}</td>
            </tr>`;
        }).join('');
    } catch(e) { tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#555">No disponible</td></tr>'; }
}

async function fetchVersion() {
    const el = document.getElementById('version-tag');
    if (!el) return;
    try {
        const res = await fetch('/version.txt');
        if (res.ok) el.innerText = `Update Actual: v${(await res.text()).trim()}`;
    } catch(e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    fetchVersion();
    loadHomeSessions();
    setInterval(loadHomeSessions, 60000);
});
