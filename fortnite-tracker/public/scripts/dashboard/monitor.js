/* ===== monitor.js – Orquestador Principal ===== */
let API_BASE = "";
let SUPABASE_URL = "";
let SUPABASE_ANON_KEY = "";
let sbClient = null;
let sessionUser = null; // Datos de Auth
let userProfile = null; // Datos de la tabla profiles
let pinnedFriendId = null;

async function initApp() {
  updateClocks();
  setInterval(updateClocks, 1000);

  try {
    const res = await fetch("/api/public-config");
    const data = await res.json();

    API_BASE = data.api_base || "";
    SUPABASE_URL = data.supabase_url;
    SUPABASE_ANON_KEY = data.supabase_anon_key;

    if (window.supabase) {
      sbClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      // checkAuth está en auth.js
      if (typeof checkAuth === "function") checkAuth();
    }
  } catch (err) {
    console.error("Error al iniciar aplicación:", err);
  }
}

function updateInicioView() {
  const emptyState = document.getElementById("empty-state-card");
  const monitorContent = document.getElementById("monitor-content");

  if (pinnedFriendId) {
    emptyState?.classList.add("hidden");
    monitorContent?.classList.remove("hidden");
    loadAppStatusData(); // Definida en friends.js
  } else {
    emptyState?.classList.remove("hidden");
    monitorContent?.classList.add("hidden");
  }
}

function updateClocks() {
  const clock = document.getElementById("clock-es");
  if (clock) clock.innerText = new Date().toLocaleTimeString("es-ES");
}

window.addEventListener("DOMContentLoaded", initApp);
