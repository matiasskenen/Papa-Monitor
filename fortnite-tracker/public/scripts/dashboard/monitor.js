/* ===== monitor.js – Orquestador Principal ===== */
let API_BASE = "";
let SUPABASE_URL = "";
let SUPABASE_ANON_KEY = "";
let sbClient = null;
let sessionUser = null;
let userProfile = null;
let pinnedFriendId = null;

async function initApp() {
  updateClocks();
  setInterval(updateClocks, 1000);

  try {
    const res = await fetch("/api/public-config");
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`/api/public-config devolvió ${res.status}: ${body.slice(0, 180)}`);
    }

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const body = await res.text();
      throw new Error(`Respuesta no JSON en /api/public-config: ${body.slice(0, 180)}`);
    }

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
  } catch (err) {
    console.error("Error al iniciar:", err);
  }
}

window.addEventListener("DOMContentLoaded", initApp);
