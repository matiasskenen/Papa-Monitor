function updateBootProgress(pct, text) {
  const bar = document.getElementById("boot-bar");
  const status = document.getElementById("boot-status");
  if (bar) bar.style.width = pct + "%";
  if (status) status.innerText = text;

  if (pct >= 100) {
    setTimeout(() => {
      const loader = document.getElementById("initial-loader");
      if (loader) loader.style.opacity = "0";
      setTimeout(() => {
        if (loader) loader.style.display = "none";
        const content = document.getElementById("app-content");
        if (content) content.style.opacity = "1";
      }, 500);
    }, 800);
  }
}

function setLoginLoading(isLoading) {
  const btn = document.getElementById("google-login-btn");
  const spinner = document.getElementById("login-spinner");
  const icon = document.getElementById("google-icon");
  const text = document.getElementById("login-btn-text");
  const err = document.getElementById("login-error-msg");

  if (isLoading) {
    btn.classList.add("opacity-80", "pointer-events-none");
    spinner.classList.remove("hidden");
    icon.classList.add("hidden");
    text.innerText = "Cargando sesión...";
    err.classList.add("hidden");
  } else {
    btn.classList.remove("opacity-80", "pointer-events-none");
    spinner.classList.add("hidden");
    icon.classList.remove("hidden");
    text.innerText = "Continuar con Google";
  }
}

function setLoginError(msg) {
  setLoginLoading(false);
  const err = document.getElementById("login-error-msg");
  err.innerText = msg;
  err.classList.remove("hidden");
}

function scrollLogsView() {
  const blk = document.getElementById("log-box");
  if (blk) blk.scrollIntoView({ behavior: "smooth", block: "center" });
}

function startInstall() {
  document.getElementById("install-action-box").style.display = "none";
  const pbox = document.getElementById("install-progress-box");
  pbox.classList.remove("hidden");

  setTimeout(() => {
    document.getElementById("install-bar").style.width = "40%";
  }, 100);
  setTimeout(() => {
    document.getElementById("install-text").innerText = "Instalando Tarea en Windows...";
  }, 1000);
  setTimeout(() => {
    document.getElementById("install-bar").style.width = "90%";
  }, 1500);

  setTimeout(() => {
    if (window.pywebview) window.pywebview.api.reparar_tarea();
  }, 2000);
}

function startUninstall() {
  document.getElementById("uninstall-action-box").style.display = "none";
  const pbox = document.getElementById("uninstall-progress-box");
  pbox.classList.remove("hidden");

  setTimeout(() => {
    document.getElementById("uninstall-bar").style.width = "50%";
  }, 100);
  setTimeout(() => {
    document.getElementById("uninstall-text").innerText = "Eliminando Tareas y Matando Servicio...";
  }, 1000);
  setTimeout(() => {
    document.getElementById("uninstall-bar").style.width = "100%";
  }, 1500);

  setTimeout(() => {
    if (window.pywebview) window.pywebview.api.desinstalar_tarea();
  }, 2000);
}
