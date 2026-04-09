/* ===== auth-bridge.js – Puente de Autenticación v2 ===== */
(function () {
  const urlParams = new URLSearchParams(window.location.search);
  const sid = urlParams.get("auth_sid");
  const hash = window.location.hash.substring(1);
  const hashParams = new URLSearchParams(hash);
  const token = hashParams.get("access_token");

  if (sid && token) {
    console.log("🔄 Registrando token en servidor para sesión:", sid);
    fetch("/api/auth/session/set?session_id=" + sid + "&token=" + token)
      .then(() => {
        window.location.hash = "";
        history.replaceState(null, "", window.location.pathname);
      })
      .catch((err) => console.error("❌ Error en el puente de auth:", err));
  }

  // Fallback puerto local para la App de escritorio (v1)
  if (token && !sid) {
    fetch("http://localhost:5555/save-token?" + hash, { mode: "no-cors" }).catch(() => {});
  }
})();
