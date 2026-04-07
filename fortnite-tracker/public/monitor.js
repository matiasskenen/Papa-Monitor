/* ===== monitor.js – lógica del panel multiusuario ===== */
let API_BASE = "";
let SUPABASE_URL = "";
let SUPABASE_ANON_KEY = "";
let sbClient = null;
let sessionUser = null;
let userProfile = null;
let pinnedFriendId = null;

const OPT_ES = { timeZone: 'Europe/Madrid', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' };
const OPT_AR = { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit' };
let detailChart = null;

// Helpers
function getUrl(path) {
    if (!API_BASE && path.startsWith('/')) {
        return window.location.origin.startsWith('http') ? path : null;
    }
    return API_BASE + path;
}

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

// ── Navegación UI ──
function showSection(id, btn) {
    document.querySelectorAll('.content-section').forEach(s => s.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('sidebar-item-active', 'text-white');
        b.classList.add('text-slate-400');
        const svg = b.querySelector('svg');
        if (svg) svg.classList.remove('text-indigo-400');
    });

    const target = document.getElementById(id);
    if (target) target.classList.remove('hidden');
    
    btn.classList.add('sidebar-item-active', 'text-white');
    btn.classList.remove('text-slate-400');
    const svg = btn.querySelector('svg');
    if (svg) svg.classList.add('text-indigo-400');

    if (id === 'graficos') loadGraficos();
    if (id === 'amigos') loadFriendsData();
    window.scrollTo(0, 0);
}

function updateClocks() {
    const opt = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
    try {
        const esClock = document.getElementById('clock-es');
        if (esClock) esClock.textContent = new Intl.DateTimeFormat('es-ES', { ...opt, timeZone: 'Europe/Madrid' }).format(new Date());
    } catch(e) {}
}

// ── Inicialización Supabase ──
async function initApp() {
    updateClocks();
    setInterval(updateClocks, 1000);

    // Fetch config
    try {
        const res = await fetch('/api/public-config');
        const data = await res.json();
        API_BASE = data.api_base || "";
        SUPABASE_URL = data.supabase_url;
        SUPABASE_ANON_KEY = data.supabase_anon_key;

        if (window.supabase) {
            sbClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
            checkAuth();
        } else {
            console.error("Supabase SDK no cargado.");
        }
    } catch(err) {
        console.error("Error al iniciar:", err);
    }
}

// ── Autenticación ──
async function checkAuth() {
    const { data: { session } } = await sbClient.auth.getSession();
    
    // Configurar listener para la UI de PyWebView donde la URL de respuesta tenga el token
    sbClient.auth.onAuthStateChange((event, session) => {
        if (session) {
            if (window.pywebview) {
                // Notificarle a Python el JWT para que lo guarde y use
                window.pywebview.api.log("Enviando token a Python...", "SYS", "blue");
                if (window.pywebview.api.save_token) {
                    window.pywebview.api.save_token(session.access_token);
                }
            }
            handleLoginSuccess(session.user);
        } else {
            handleLogoutState();
        }
    });

    if (session) {
        handleLoginSuccess(session.user);
    } else {
        handleLogoutState();
    }
}

document.getElementById('btn-login-google').addEventListener('click', async () => {
    // Si estamos en Pywebview, supabase intentará abrir popup/redirect.
    const { data, error } = await sbClient.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: window.location.origin + '/dashboard'
        }
    });
    if (error) {
        document.getElementById('login-status-msg').textContent = "Error: " + error.message;
    }
});

async function logout() {
    await sbClient.auth.signOut();
}

function handleLogoutState() {
    document.getElementById('login-view').classList.remove('hidden');
    document.getElementById('app-view').classList.add('hidden');
    sessionUser = null;
    userProfile = null;
    pinnedFriendId = null;
}

async function handleLoginSuccess(user) {
    sessionUser = user;
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('app-view').classList.remove('hidden');
    
    // Cargar perfil propio
    await loadMyProfile();
    
    // Iniciar loop de monitor
    loadAppStatusData();
    setInterval(loadAppStatusData, 15000);
}

// ── Perfiles y Amigos ──
async function loadMyProfile() {
    const { data, error } = await sbClient.from('users_profiles').select('*').eq('id', sessionUser.id).single();
    if (data) {
        userProfile = data;
        pinnedFriendId = data.pinned_friend_id;
        
        document.getElementById('my-friend-code').textContent = data.friend_code || "------";
        document.getElementById('my-display-name').value = data.display_name || "";
        
        const avatarEl = document.getElementById('user-avatar');
        const fallbackEl = document.getElementById('user-avatar-fallback');
        if (data.display_name) {
            fallbackEl.textContent = data.display_name.substring(0, 2).toUpperCase();
        }
        
        updateInicioView();
    }
}

async function copyMyID() {
    if (userProfile && userProfile.friend_code) {
        navigator.clipboard.writeText(userProfile.friend_code);
        alert("¡ID copiado al portapapeles!");
    }
}

async function copyTrackerToken() {
    const session = await sbClient.auth.getSession();
    if (session.data && session.data.session) {
        const token = session.data.session.access_token;
        navigator.clipboard.writeText(token);
        const btnText = document.getElementById('copy-token-text');
        btnText.textContent = "¡Copiado!";
        setTimeout(() => {
            btnText.textContent = "Copiar Token Seguro";
        }, 2000);
    } else {
        alert("Error al obtener la sesión");
    }
}

async function updateProfile() {
    const newName = document.getElementById('my-display-name').value;
    if (!newName) return;
    const { error } = await sbClient.from('users_profiles').update({ display_name: newName }).eq('id', sessionUser.id);
    if (!error) {
        alert("Perfil actualizado correctamente");
        loadMyProfile();
    }
}

async function loadFriendsData() {
    // Cargar pendientes a mí
    const { data: pending } = await sbClient.from('friends').select('id, user_id, status, users_profiles!friends_user_id_fkey(display_name)').eq('friend_id', sessionUser.id).eq('status', 'pending');
    
    const pendCont = document.getElementById('pending-requests-container');
    const pendList = document.getElementById('pending-friends-list');
    
    if (pending && pending.length > 0) {
        pendCont.classList.remove('hidden');
        pendList.innerHTML = pending.map(p => `
            <div class="flex items-center justify-between bg-white/5 p-3 rounded-xl border border-rose-500/20">
                <span class="font-bold">${p.users_profiles.display_name}</span>
                <div class="flex gap-2">
                    <button onclick="acceptFriend('${p.id}')" class="px-3 py-1 bg-emerald-500/20 text-emerald-400 font-bold rounded hover:bg-emerald-500/30">Aceptar</button>
                    <button onclick="rejectFriend('${p.id}')" class="px-3 py-1 bg-rose-500/20 text-rose-400 font-bold rounded hover:bg-rose-500/30">X</button>
                </div>
            </div>
        `).join('');
    } else {
        pendCont.classList.add('hidden');
        pendList.innerHTML = '';
    }

    // Cargar mis amigos (donde soy user_id o friend_id, y status='accepted')
    const { data: friendsData } = await sbClient.from('friends').select(`
        id, status, user_id, friend_id,
        user_profile:users_profiles!friends_user_id_fkey(id, display_name, friend_code),
        friend_profile:users_profiles!friends_friend_id_fkey(id, display_name, friend_code)
    `).or(`user_id.eq.${sessionUser.id},friend_id.eq.${sessionUser.id}`).eq('status', 'accepted');

    const fList = document.getElementById('friends-list');
    if (friendsData && friendsData.length > 0) {
        fList.innerHTML = friendsData.map(f => {
            // Determinar quién es el amigo
            const friendProf = f.user_id === sessionUser.id ? f.friend_profile : f.user_profile;
            const isPinned = pinnedFriendId === friendProf.id;
            
            return `
            <div class="flex items-center justify-between bg-white/5 hover:bg-white/10 transition-colors p-4 rounded-xl border ${isPinned ? 'border-indigo-500' : 'border-white/5'}">
                <div>
                    <h4 class="font-bold text-lg flex items-center gap-2">
                        ${friendProf.display_name}
                        ${isPinned ? '<span class="px-2 py-0.5 rounded text-[10px] bg-indigo-500 text-white uppercase tracking-widest font-black">FIJADO</span>' : ''}
                    </h4>
                    <span class="text-xs text-slate-400">ID: ${friendProf.friend_code}</span>
                </div>
                <div class="flex items-center gap-3">
                    ${!isPinned ? `<button onclick="pinFriend('${friendProf.id}')" class="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/20 text-indigo-400 font-bold rounded-lg hover:bg-indigo-500/30 transition-colors tooltip" aria-label="Monitorear">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                        Ver
                    </button>` : ''}
                    <button onclick="removeFriend('${f.id}')" class="text-slate-500 hover:text-rose-400 transition-colors p-2"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
                </div>
            </div>`;
        }).join('');
    } else {
        fList.innerHTML = `<div class="text-center py-10 text-slate-500 font-medium">Aún no tienes amigos añadidos.</div>`;
    }
}

async function sendFriendRequest() {
    const input = document.getElementById('friend-search-input').value.trim();
    const msgEl = document.getElementById('add-friend-msg');
    msgEl.textContent = "";
    
    if (!input) return;
    
    // Buscar usuario por código de amigo
    const { data: targetUser } = await sbClient.from('users_profiles').select('id').eq('friend_code', input).single();
    
    if (!targetUser) {
        msgEl.textContent = "Usuario no encontrado.";
        msgEl.className = "text-sm font-medium h-4 text-rose-400 text-center";
        return;
    }
    
    if (targetUser.id === sessionUser.id) {
        msgEl.textContent = "No puedes agregarte a ti mismo.";
        return;
    }
    
    // Consultar si ya existe
    const { data: existing } = await sbClient.from('friends').select('*').or(`and(user_id.eq.${sessionUser.id},friend_id.eq.${targetUser.id}),and(user_id.eq.${targetUser.id},friend_id.eq.${sessionUser.id})`);
    
    if (existing && existing.length > 0) {
        msgEl.textContent = "Ya enviaste o tienes una conexión con este usuario.";
        msgEl.className = "text-sm font-medium h-4 text-rose-400 text-center";
        return;
    }

    const { error } = await sbClient.from('friends').insert({ user_id: sessionUser.id, friend_id: targetUser.id, status: 'pending' });
    if (!error) {
        msgEl.textContent = "Solicitud enviada correctamente.";
        msgEl.className = "text-sm font-medium h-4 text-emerald-400 text-center";
        document.getElementById('friend-search-input').value = "";
    } else {
        msgEl.textContent = "Error al enviar: " + error.message;
    }
}

async function acceptFriend(id) {
    await sbClient.from('friends').update({ status: 'accepted' }).eq('id', id);
    loadFriendsData();
}

async function rejectFriend(id) {
    await sbClient.from('friends').delete().eq('id', id);
    loadFriendsData();
}

async function removeFriend(id) {
    if (confirm("¿Estás seguro de que quieres eliminar a este amigo?")) {
        await sbClient.from('friends').delete().eq('id', id);
        // Si estaba fijado, des-fijarlo si es que de hecho era él (logica simple, limpiaremos el pinnedId del perfil)
        // por pereza recargaremos el perfil completo
        loadMyProfile();
        loadFriendsData();
    }
}

async function pinFriend(targetUserId) {
    const { error } = await sbClient.from('users_profiles').update({ pinned_friend_id: targetUserId }).eq('id', sessionUser.id);
    if (!error) {
        pinnedFriendId = targetUserId;
        loadFriendsData();
        updateInicioView();
        loadAppStatusData(); // Recargar datos de monitor
    }
}

function updateInicioView() {
    if (!pinnedFriendId) {
        document.getElementById('empty-state-card').classList.remove('hidden');
        document.getElementById('monitor-content').classList.add('hidden');
    } else {
        document.getElementById('empty-state-card').classList.add('hidden');
        document.getElementById('monitor-content').classList.remove('hidden');
        
        // Cargar nombre del amigo
        sbClient.from('users_profiles').select('display_name').eq('id', pinnedFriendId).single().then(({data}) => {
            if (data) {
                document.getElementById('pinned-friend-name').textContent = data.display_name;
            }
        });
    }
}

// ── Estado (Monitor) ──
async function loadAppStatusData() {
    if (!userProfile || !pinnedFriendId) return;

    // Buscar sesiones recientes de ese usuario
    const { data: sessions } = await sbClient.from('sessions')
        .select('*')
        .eq('user_id', pinnedFriendId)
        .order('start_time', { ascending: false })
        .limit(10);

    const list = document.getElementById('last-sessions-list');
    
    if (!sessions || sessions.length === 0) { 
        list.innerHTML = '<div class="glass p-6 text-center text-slate-500 rounded-xl">Sin actividad reciente</div>';
        return;
    }
    
    list.innerHTML = sessions.slice(0, 3).map((s, i) => {
        const sesNumber = sessions.length - i;
        const dateStr = fmt(s.start_time, { day: 'numeric', month: 'short', year: 'numeric' });
        
        const esStart = fmt(s.start_time, { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid' });
        const esEnd = s.is_active ? 'Ahora' : fmt(s.end_time, { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid' });
        const duration = getDur(s.start_time, s.end_time, s.is_active);

        return `
            <div class="glass p-4 sm:p-5 rounded-2xl flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <div class="w-10 h-10 shrink-0 rounded-xl ${s.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400'} flex items-center justify-center">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    </div>
                    <div>
                        <div class="flex items-baseline gap-2">
                            <h4 class="font-bold text-white text-sm">Sesión</h4>
                            <span class="text-[10px] text-slate-500">${dateStr}</span>
                        </div>
                        <div class="text-xs text-slate-400 mt-1">${esStart} — ${esEnd} <span class="text-indigo-400 ml-2 font-bold">${duration}</span></div>
                    </div>
                </div>
                <div class="text-right flex flex-col items-end">
                    <span class="text-[9px] text-slate-500 uppercase font-bold tracking-widest mb-0.5">Estado</span>
                    <span class="text-xs font-black ${s.is_active ? 'text-emerald-400' : 'text-slate-300'}">${s.is_active ? 'En curso' : 'Cerrada'}</span>
                </div>
            </div>`;
    }).join('');

    const top = sessions[0];
    const stEl = document.getElementById('status-text');
    const ptEl = document.getElementById('play-time');
    const glow = document.getElementById('status-glow');

    if (top && top.is_active) {
        stEl.textContent = 'ONLINE';
        stEl.className = "text-5xl sm:text-7xl font-black mb-4 tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-emerald-400 to-emerald-600";
        glow.className = "absolute -top-24 -left-24 w-64 h-64 bg-emerald-500/20 blur-[100px] rounded-full transition-colors duration-1000";
        ptEl.innerHTML = `<span class="text-emerald-400 font-bold items-center flex gap-2 justify-center"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>Transmitiendo actividad</span>`;
    } else {
        stEl.textContent = 'OFFLINE';
        stEl.className = "text-5xl sm:text-7xl font-black mb-4 tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40";
        glow.className = "absolute -top-24 -left-24 w-64 h-64 bg-rose-500/20 blur-[100px] rounded-full transition-colors duration-1000";
        
        if (top && top.end_time) {
            ptEl.textContent = `Inactivo desde hace ${getDur(top.end_time, new Date(), false)}`;
        } else {
            ptEl.textContent = 'El sistema se encuentra desconectado.';
        }
    }
}

// ── Gráficos ──
async function loadGraficos() {
    if (!pinnedFriendId) return;

    const { data: sessions } = await sbClient.from('sessions').select('*')
        .eq('user_id', pinnedFriendId)
        .order('start_time', { ascending: false })
        .limit(30);

    const tbody = document.querySelector('#sessions-table tbody');
    if (tbody) {
        tbody.innerHTML = (sessions || []).map(s => `
            <tr class="hover:bg-white/[0.02] transition-colors border-b border-white/5 last:border-0 text-sm">
                <td class="py-3 text-slate-300 font-medium">${fmt(s.start_time, OPT_ES)}</td>
                <td class="py-3 text-slate-400">${s.is_active ? '—' : fmt(s.end_time, OPT_ES)}</td>
                <td class="py-3 text-indigo-300 font-mono">${getDur(s.start_time, s.end_time, s.is_active)}</td>
            </tr>`).join('') || `<tr><td colspan="3" class="text-center py-10 text-slate-500">Sin sesiones registradas</td></tr>`;
    }

    // Chart logic
    if (sessions && sessions.length > 0) {
        // ... (Omitting chart logic detail for brevity, it's mostly ChartJS mapping)
    }
}

// ── INIT ──
window.addEventListener('DOMContentLoaded', initApp);
