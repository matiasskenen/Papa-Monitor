/* ===== ui.js – Gestión de Interfaz ===== */
function updateClocks() {
  const opt = { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false };
  try {
    const esClock = document.getElementById("clock-es");
    if (esClock) esClock.textContent = new Intl.DateTimeFormat("es-ES", { ...opt, timeZone: "Europe/Madrid" }).format(new Date());
  } catch (e) {}
}

function showSection(id, btn) {
  document.querySelectorAll(".content-section").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.remove("sidebar-item-active", "text-white");
    b.classList.add("text-slate-400");
    const svg = b.querySelector("svg");
    if (svg) svg.classList.remove("text-indigo-400");
  });

  const target = document.getElementById(id);
  if (target) target.classList.add("active");

  btn.classList.add("sidebar-item-active", "text-white");
  btn.classList.remove("text-slate-400");
  const svg = btn.querySelector("svg");
  if (svg) svg.classList.add("text-indigo-400");

  if (id === "graficos") loadGraficos();
  if (id === "amigos") loadFriendsData();
  window.scrollTo(0, 0);
}

// Helpers globales de formato
function fmt(iso, opts) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : new Intl.DateTimeFormat("es-ES", opts).format(d);
}

function getDur(start, end, active) {
  const a = new Date(start);
  const b = active ? new Date() : end ? new Date(end) : null;
  if (!b || isNaN(a.getTime())) return "—";
  const mins = Math.max(0, Math.floor((b - a) / 60000));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return (h > 0 ? h + "h " : "") + m + "m";
}

/* ===== Actualización Dinámica del Inicio corregida para tu HTML ===== */
async function updateInicioView() {
    const emptyState = document.getElementById("empty-state-card");
    const monitorContent = document.getElementById("monitor-content");
    const pinnedNameLabel = document.getElementById("pinned-friend-name");
    const statusText = document.getElementById("status-text");
    const statusGlow = document.getElementById("status-glow");

    // Si no hay nadie fijado, mostramos el mensaje de "Selecciona un amigo"
    if (!pinnedFriendId) {
        if (emptyState) emptyState.classList.remove("hidden");
        if (monitorContent) monitorContent.classList.add("hidden");
        return;
    }

    // Si hay alguien, mostramos el dashboard de monitoreo
    if (emptyState) emptyState.classList.add("hidden");
    if (monitorContent) monitorContent.classList.remove("hidden");

    try {
        // 1. Obtener el nombre del amigo fijado desde la tabla de perfiles
        const { data: friend } = await sbClient
            .from("users_profiles")
            .select("username")
            .eq("id", pinnedFriendId)
            .maybeSingle();

        if (friend && pinnedNameLabel) {
            pinnedNameLabel.innerText = friend.username;
        }

        // 2. Verificar si tiene una sesión activa en la tabla 'sessions'
        const { data: activeSession } = await sbClient
            .from("sessions")
            .select("is_active")
            .eq("user_id", pinnedFriendId)
            .eq("is_active", true)
            .maybeSingle();

        if (activeSession) {
            if (statusText) {
                statusText.innerText = "ONLINE";
                statusText.classList.add("text-indigo-400");
                statusText.classList.remove("text-transparent"); // Para que se vea bien el gradiente o color
            }
            if (statusGlow) {
                statusGlow.classList.replace("bg-rose-500/20", "bg-indigo-500/40");
            }
        } else {
            if (statusText) {
                statusText.innerText = "OFFLINE";
                statusText.classList.remove("text-indigo-400");
            }
            if (statusGlow) {
                statusGlow.classList.replace("bg-indigo-500/40", "bg-rose-500/20");
            }
        }

        // 3. Cargar las barritas de las últimas sesiones (la función que ya tienes en friends.js)
        if (typeof loadAppStatusData === "function") {
            loadAppStatusData();
        }

    } catch (err) {
        console.error("Error al actualizar la vista:", err);
    }
}