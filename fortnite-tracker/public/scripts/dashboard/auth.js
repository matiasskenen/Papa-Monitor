/* ===== auth.js – Gestión de Autenticación ===== */

async function checkAuth() {
  const {
    data: { session },
  } = await sbClient.auth.getSession();
  if (session) {
    handleLoginSuccess(session.user);
  } else {
    document.getElementById("login-view").classList.remove("hidden");
    document.getElementById("app-view").classList.add("hidden");
  }
}

async function handleLoginSuccess(user) {
  sessionUser = user;

  // UI Update
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.remove("hidden");

  const avatarImg = document.getElementById("user-avatar");
  if (user.user_metadata.avatar_url) {
    avatarImg.src = user.user_metadata.avatar_url;
    avatarImg.classList.remove("hidden");
    document.getElementById("user-avatar-fallback").classList.add("hidden");
  }

  // Cargar perfil del usuario (esta función está en friends.js)
  await loadMyProfile();
}

async function logout() {
  await sbClient.auth.signOut();
  location.reload();
}

// Evento para el botón de Google
document.getElementById("btn-login-google")?.addEventListener("click", async () => {
  await sbClient.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
});
