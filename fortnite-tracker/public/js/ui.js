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
