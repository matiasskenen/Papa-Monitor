const API = '';
const fb = document.getElementById('feedback');

const headers = () => ({ 'Content-Type': 'application/json' });

function parseProcessField(raw) {
    const s = (raw || '').trim();
    if (!s) return ['FortniteClient-Win64-Shipping'];
    if (s.startsWith('[')) return JSON.parse(s);
    return s.split(',').map(x => x.trim()).filter(Boolean);
}

document.getElementById('btn-load').addEventListener('click', async () => {
    fb.textContent = '';
    fb.className = 'msg';
    try {
        const res = await fetch(API + '/api/admin/settings', { headers: headers() });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || res.statusText);
        document.getElementById('emails_enabled').checked = data.emails_enabled === true || data.emails_enabled === 'true';
        document.getElementById('alert_email').value = data.alert_email || '';
        document.getElementById('resend_from').value = data.resend_from || '';
        document.getElementById('poll_interval_seconds').value = data.poll_interval_seconds || '20';
        let p = data.process_substrings;
        if (typeof p === 'string' && p.startsWith('[')) {
            try { p = JSON.parse(p); } catch (_) {}
        }
        if (Array.isArray(p)) {
            document.getElementById('process_substrings').value = JSON.stringify(p, null, 0);
        } else {
            document.getElementById('process_substrings').value = String(p || '');
        }
        fb.textContent = 'Valores cargados.';
        fb.classList.add('ok');
    } catch (e) {
        fb.textContent = String(e.message || e);
        fb.classList.add('err');
    }
});

document.getElementById('btn-save').addEventListener('click', async () => {
    fb.textContent = '';
    fb.className = 'msg';
    try {
        let proc;
        try {
            proc = parseProcessField(document.getElementById('process_substrings').value);
        } catch (e) {
            throw new Error('JSON inválido en procesos');
        }
        const body = {
            emails_enabled: document.getElementById('emails_enabled').checked,
            alert_email: document.getElementById('alert_email').value.trim(),
            resend_from: document.getElementById('resend_from').value.trim(),
            poll_interval_seconds: document.getElementById('poll_interval_seconds').value.trim() || '20',
            process_substrings: proc,
        };
        const res = await fetch(API + '/api/admin/settings', {
            method: 'POST',
            headers: headers(),
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || res.statusText);
        fb.textContent = 'Guardado correctamente.';
        fb.classList.add('ok');
    } catch (e) {
        fb.textContent = String(e.message || e);
        fb.classList.add('err');
    }
});

// --- BOTONES DE PRUEBA ---
const tfb = document.getElementById('test-feedback');

document.getElementById('btn-test-email').addEventListener('click', async () => {
    tfb.textContent = 'Enviando email de prueba...';
    tfb.className = 'msg';
    try {
        const res = await fetch(API + '/api/test-email', {
            method: 'POST',
            headers: headers(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || res.statusText);
        tfb.textContent = '✅ ' + (data.message || 'Email enviado correctamente.');
        tfb.classList.add('ok');
    } catch (e) {
        tfb.textContent = '❌ Error: ' + String(e.message || e);
        tfb.classList.add('err');
    }
});

// Cargar valores automáticamente al abrir la página
document.getElementById('btn-load').click();
