/* ===== auth.js – Gestión de Usuarios ===== */
async function checkAuth() {
  const {
    data: { session },
  } = await sbClient.auth.getSession();

  sbClient.auth.onAuthStateChange(async (event, currentSession) => {
    if (currentSession) {
      handleLoginSuccess(currentSession.user);
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

async function handleLoginSuccess(user) {
  sessionUser = user;
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.remove("hidden");

  await loadMyProfile();
  loadAppStatusData();
  setInterval(loadAppStatusData, 15000);
}

function handleLogoutState() {
  document.getElementById("login-view").classList.remove("hidden");
  document.getElementById("app-view").classList.add("hidden");
}

// Evento del botón de Google
document.getElementById("btn-login-google").addEventListener("click", async () => {
  await sbClient.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin + "/dashboard" },
  });
});
