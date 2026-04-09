// Funciones UI base movidas a ./assets/js/dashboard-actions.js

// Inicialización al cargar la ventana
window.addEventListener("load", () => {
  // Remover el spinner y desvanecer la entrada de la app
  setTimeout(() => {
    const loader = document.getElementById("initial-loader");
    if (loader) loader.style.display = "none";
    const content = document.getElementById("app-content");
    if (content) content.style.opacity = "1";
  }, 500);
});

// Notificar al motor que el HTML está listo (vía evento específico de pywebview)
window.addEventListener("pywebviewready", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.loaded();
  }
});

let updateTimer = null;
let sessionStart = null;
let myChart = null;

function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach((el) => el.classList.add("hidden"));
  document.getElementById("section-" + tabId).classList.remove("hidden");

  document.querySelectorAll(".sidebar-item").forEach((el) => {
    el.classList.remove("active");
    el.classList.add("text-neutral-500");
  });
  document.getElementById("btn-" + tabId).classList.add("active");
  document.getElementById("btn-" + tabId).classList.remove("text-neutral-500");

  if (tabId === "stats") {
    loadStats();
  } else if (tabId === "friends") {
    loadFriends();
  }
}

async function fetchApi(path, options = {}) {
  if (!window.pywebview) return null;
  const ctx = await window.pywebview.api.get_api_context();
  if (!ctx || !ctx.token) return null;

  const res = await fetch(`${ctx.api_base}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${ctx.token}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  return await res.json();
}

async function loadFriends() {
  const profile = await fetchApi("/api/friends/profile");
  if (profile && profile.friend_code) {
    document.getElementById("my-friend-code").innerText = profile.friend_code;
  }

  const data = await fetchApi("/api/friends/list");
  if (!data) return;

  const reqBox = document.getElementById("requests-container");
  const reqList = document.getElementById("requests-list");

  if (data.requests && data.requests.length > 0) {
    reqBox.classList.remove("hidden");
    reqList.innerHTML = data.requests
      .map(
        (r) => `
          <div class="flex items-center justify-between p-3 bg-black/40 rounded-xl border border-white/5">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-yellow-500/20 text-yellow-500 flex items-center justify-center font-bold">
                ${r.requester.display_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <p class="text-[10px] font-bold text-white uppercase">${r.requester.display_name}</p>
                <p class="text-[8px] font-mono text-neutral-500">ID: ${r.requester.friend_code}</p>
              </div>
            </div>
            <button onclick="acceptRequest('${r.id}')" class="px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-black uppercase text-[9px] tracking-widest rounded-lg transition-colors">
              Aceptar
            </button>
          </div>
        `,
      )
      .join("");
  } else {
    reqBox.classList.add("hidden");
    reqList.innerHTML = "";
  }

  const friendsList = document.getElementById("friends-list");
  if (data.friends && data.friends.length > 0) {
    friendsList.innerHTML = data.friends
      .map(
        (f) => `
          <div class="flex items-center justify-between p-4 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 rounded-2xl transition-colors">
            <div class="flex items-center gap-4">
              <div class="relative w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold border border-blue-500/30">
                ${f.friend?.display_name?.charAt(0)?.toUpperCase()}
                <div class="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-[#0c0c10]"></div>
              </div>
              <div>
                <p class="text-xs font-bold text-white uppercase tracking-widest">${f.friend?.display_name || "Desconocido"}</p>
                <p class="text-[9px] font-mono text-blue-400">ID: ${f.friend?.friend_code || "---"}</p>
              </div>
            </div>
          </div>
        `,
      )
      .join("");
  } else {
    friendsList.innerHTML = `
          <div class="col-span-full flex flex-col items-center justify-center py-10 opacity-50">
             <svg class="w-12 h-12 text-neutral-600 mb-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m22 11-3-3-3 3"/><path d="M19 8v13"/></svg>
             <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-400">Tu lista está vacía</p>
          </div>
        `;
  }
}

async function addFriendRequest() {
  const code = document.getElementById("add-friend-input").value.trim();
  const msg = document.getElementById("add-friend-msg");
  msg.classList.remove("hidden", "text-green-500", "text-red-500");

  if (!code) {
    msg.innerText = "Ingresa un código válido.";
    msg.classList.add("text-red-500");
    return;
  }

  msg.innerText = "Buscando...";
  msg.classList.add("text-blue-500");

  const data = await fetchApi("/api/friends/add", {
    method: "POST",
    body: JSON.stringify({ code }),
  });

  if (data.status === "ok") {
    msg.innerText = "Petición enviada con éxito.";
    msg.className = "text-[9px] font-bold uppercase tracking-widest mt-3 text-green-500";
    document.getElementById("add-friend-input").value = "";
  } else {
    msg.innerText = data.error || "Error al enviar petición.";
    msg.className = "text-[9px] font-bold uppercase tracking-widest mt-3 text-red-500";
  }
}

async function acceptRequest(id) {
  await fetchApi("/api/friends/accept", {
    method: "POST",
    body: JSON.stringify({ request_id: id }),
  });
  loadFriends();
}

async function loadStats() {
  if (!window.pywebview || !window.pywebview.api) return;

  const stats = await window.pywebview.api.get_stats();
  const totalHrs = Math.floor(stats.total_minutes / 60);
  const totalMins = stats.total_minutes % 60;

  document.getElementById("total-hours").innerText = `${totalHrs}h ${totalMins}m`;

  const history = stats.history || {};
  const labels = Object.keys(history).sort();
  const values = labels.map((l) => history[l]);

  document.getElementById("total-days").innerText = labels.length;

  const chartBox = document.getElementById("chart-container");
  const msgBox = document.getElementById("no-stats-msg");

  if (labels.length === 0) {
    chartBox.classList.add("hidden");
    msgBox.classList.remove("hidden");
    return;
  } else {
    chartBox.classList.remove("hidden");
    msgBox.classList.add("hidden");
  }

  if (myChart) myChart.destroy();

  const ctx = document.getElementById("sessionsChart").getContext("2d");
  myChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels.map((l) => l.split("-").slice(1).join("/")),
      datasets: [
        {
          label: "Minutos jugados",
          data: values,
          backgroundColor: "rgba(99, 102, 241, 0.5)",
          borderColor: "#6366f1",
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1f2937",
          titleColor: "#9ca3af",
          bodyColor: "#fff",
          bodyFont: { weight: "bold" },
          padding: 12,
          cornerRadius: 12,
          displayColors: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
          ticks: { color: "#666", font: { size: 10, weight: "bold" } },
        },
        x: {
          grid: { display: false },
          ticks: { color: "#666", font: { size: 10, weight: "bold" } },
        },
      },
    },
  });
}

function setVersion(v) {
  document.getElementById("installer-version").innerText = "Build " + v;
  document.getElementById("dashboard-version").innerText = "v" + v + "_STABLE";
}

function setLastUpdateDate(dateStr) {
  const el = document.getElementById("last-update-date");
  if (el) el.innerText = dateStr;
}

function startDownloadUpdate() {
  document.getElementById("btn-instalar-ahora").classList.add("hidden");
  document.getElementById("update-progress-container").classList.remove("hidden");
  document.getElementById("update-progress-text").innerText = "Conectando... 0%";
  document.getElementById("update-progress-bar").style.width = "0%";

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.do_auto_update();
  }
}

function updateDownloadProgress(pct, isFinished) {
  if (isFinished || pct >= 100) {
    document.getElementById("update-progress-bar").style.width = "100%";
    document.getElementById("update-progress-text").innerText = "Preparando reinicio...";
    document.getElementById("update-progress-text").classList.replace("text-blue-400", "text-yellow-400");
    setTimeout(() => {
      document.getElementById("update-progress-text").innerText = "Cerrando aplicación...";
    }, 800);
  } else {
    document.getElementById("update-progress-bar").style.width = pct + "%";
    document.getElementById("update-progress-text").innerText = "Descargando... " + pct + "%";
  }
}

function resetDownloadUI(err) {
  document.getElementById("btn-instalar-ahora").classList.remove("hidden");
  document.getElementById("update-progress-container").classList.add("hidden");
  alert("Error de descarga: " + err);
}

function setInstallState(isInstalled) {
  if (isInstalled) {
    document.getElementById("installer-view").classList.add("hidden");
    document.getElementById("dashboard-view").classList.remove("hidden");
    document.body.classList.remove("installer-mode");
  } else {
    document.getElementById("installer-view").classList.remove("hidden");
    document.getElementById("dashboard-view").classList.add("hidden");
    document.body.classList.add("installer-mode");
  }
}

function showUpdateBanner(msg, isVersionParam) {
  const iview = document.getElementById("installer-view").classList.contains("hidden");
  if (!iview) {
    const feed = document.getElementById("installer-feedback");
    feed.innerText = msg;
    feed.classList.remove("hidden");
  } else if (isVersionParam) {
    document.getElementById("update-module").classList.remove("hidden");
    document.getElementById("update-banner-title").innerText = "Actualización " + msg + " Detectada";
  }
}

function addLog(ts, tag, tagColor, msg) {
  let tailColor = "neutral-600";
  if (tagColor === "green") tailColor = "green-500";
  if (tagColor === "red") tailColor = "red-500";
  if (tagColor === "blue") tailColor = "blue-500";

  const pre = document.getElementById("log-box");
  if (pre) {
    pre.innerHTML += `[${ts}] <span class="text-${tailColor} font-bold">${tag}:</span> ${msg}\n`;
    pre.scrollTop = pre.scrollHeight;
  }
}

function setSystemState(isOnline, startTimeIso, isLoggedIn) {
  const text = document.getElementById("status-text");
  const timer = document.getElementById("status-timer");
  const cardEdge = document.getElementById("status-card-border");
  const loginOverlay = document.getElementById("login-overlay");

  if (isLoggedIn === false) {
    loginOverlay.classList.remove("hidden");
  } else if (isLoggedIn === true) {
    loginOverlay.classList.add("hidden");
  }

  if (isOnline) {
    text.classList.remove("text-neutral-500", "text-red-500");
    text.classList.add("text-green-400");
    text.innerText = "ACTIVO";
    timer.classList.remove("hidden");
    cardEdge.classList.replace("border-l-neutral-500/50", "border-l-green-500/50");
    cardEdge.classList.replace("border-l-red-500/50", "border-l-green-500/50");

    sessionStart = startTimeIso ? new Date(startTimeIso) : new Date();
    if (updateTimer) clearInterval(updateTimer);
    updateTimer = setInterval(updateTimeRunning, 1000);
    updateTimeRunning();
  } else {
    text.classList.remove("text-green-400");
    text.classList.add("text-neutral-500");
    text.innerText = "OFFLINE";
    timer.classList.add("hidden");
    cardEdge.classList.replace("border-l-green-500/50", "border-l-neutral-500/50");

    if (updateTimer) {
      clearInterval(updateTimer);
      updateTimer = null;
    }
  }
}

function updateTimeRunning() {
  if (!sessionStart) return;
  const diff = Math.floor((new Date() - sessionStart) / 1000);
  const hrs = Math.floor(diff / 3600);
  const mins = Math.floor((diff % 3600) / 60);
  const secs = diff % 60;

  const pad = (n) => n.toString().padStart(2, "0");
  document.getElementById("status-timer").innerText = `${pad(hrs)}h ${pad(mins)}m ${pad(secs)}s`;
}

function setEmailState(isEnabled) {
  const emailToggle = document.getElementById("email-toggle");
  if (emailToggle) emailToggle.checked = !!isEnabled;
}

function handleEmailToggle(el) {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_emails(el.checked);
  }
}
