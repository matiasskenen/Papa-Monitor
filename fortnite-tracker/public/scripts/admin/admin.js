/* ===== admin.js – Lógica de administración ===== */

const feedback = document.getElementById("feedback");
const testFeedback = document.getElementById("test-feedback");

function showMsg(el, text, isError = false) {
  el.innerText = text;
  el.className = isError ? "msg error" : "msg success";
  setTimeout(() => {
    el.innerText = "";
    el.className = "msg";
  }, 3000);
}

async function loadConfig() {
  try {
    const res = await fetch("/api/admin/settings");
    if (!res.ok) throw new Error("Error al cargar configuración");
    const data = await res.json();

    document.getElementById("emails_enabled").checked = data.emails_enabled;
    document.getElementById("alert_email").value = data.alert_email || "";
    document.getElementById("resend_from").value = data.resend_from || "";
    document.getElementById("poll_interval_seconds").value = data.poll_interval_seconds || 20;
    document.getElementById("process_substrings").value = typeof data.process_substrings === "string" ? data.process_substrings : JSON.stringify(data.process_substrings);

    showMsg(feedback, "Configuración cargada");
  } catch (e) {
    showMsg(feedback, "Error al conectar con el servidor", true);
  }
}

async function saveConfig() {
  const config = {
    emails_enabled: document.getElementById("emails_enabled").checked,
    alert_email: document.getElementById("alert_email").value,
    resend_from: document.getElementById("resend_from").value,
    poll_interval_seconds: parseInt(document.getElementById("poll_interval_seconds").value),
    process_substrings: document.getElementById("process_substrings").value,
  };

  try {
    const res = await fetch("/api/admin/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (res.ok) showMsg(feedback, "Cambios guardados correctamente");
    else throw new Error();
  } catch (e) {
    showMsg(feedback, "Error al guardar los cambios", true);
  }
}

async function testEmail() {
  try {
    const res = await fetch("/api/test-email", { method: "POST" });
    if (res.ok) showMsg(testFeedback, "Email enviado con éxito");
    else throw new Error();
  } catch (e) {
    showMsg(testFeedback, "Error al enviar el email de prueba", true);
  }
}

document.getElementById("btn-load").addEventListener("click", loadConfig);
document.getElementById("btn-save").addEventListener("click", saveConfig);
document.getElementById("btn-test-email").addEventListener("click", testEmail);
document.addEventListener("DOMContentLoaded", loadConfig);
