/* ===== ui.js – Gestión de Interfaz ===== */

function showSection(sectionId, btnEl) {
  // 1. Ocultar todas las secciones
  document.querySelectorAll(".content-section").forEach((sec) => {
    sec.classList.remove("active");
  });

  // 2. Mostrar la sección seleccionada
  const target = document.getElementById(sectionId);
  if (target) target.classList.add("active");

  // 3. Actualizar estilo de los botones del sidebar
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.remove("sidebar-item-active", "text-white");
    btn.classList.add("text-slate-400");
  });

  if (btnEl) {
    btnEl.classList.add("sidebar-item-active", "text-white");
    btnEl.classList.remove("text-slate-400");
  }

  // 4. Cargar datos específicos de la sección
  if (sectionId === "amigos") {
    if (typeof loadFriendsData === "function") loadFriendsData();
  }
}

// Formateadores de utilidad
function fmt(dateStr) {
  return new Date(dateStr).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

function getDur(start, end, isActive) {
  const s = new Date(start);
  const e = isActive ? new Date() : new Date(end);
  const diffMs = e - s;
  const mins = Math.floor(diffMs / 60000);
  return mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins} min`;
}
