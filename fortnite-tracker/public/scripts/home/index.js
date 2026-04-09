/* ===== index.js – lógica del sitio público principal ===== */
const OPT_ES = { timeZone: "Europe/Madrid", dateStyle: "short", timeStyle: "short" };

function fmtZone(iso, opts) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : new Intl.DateTimeFormat("es-ES", opts).format(d);
}

async function loadHomeSessions() {
  const tbody = document.querySelector("#home-sessions tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/status?limit=10");
    if (!res.ok) throw new Error();

    const data = await res.json();

    if (!Array.isArray(data) || !data.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#888" class="py-4">Sin sesiones recientes</td></tr>';
      return;
    }

    tbody.innerHTML = data
      .slice(0, 3)
      .map((s, i) => {
        const st = s.is_active ? "ONLINE" : "OFFLINE";
        const color = s.is_active ? "text-emerald-400" : "text-slate-500";
        return `
                <tr class="border-b border-white/5 last:border-0">
                    <td class="py-3 px-2 text-slate-500 text-xs">${i + 1}</td>
                    <td class="py-3 px-2">
                        <span class="font-black text-[10px] tracking-widest ${color}">${st}</span>
                    </td>
                    <td class="py-3 px-2 text-slate-300 font-mono text-xs text-right">
                        ${fmtZone(s.start_time, OPT_ES)}
                    </td>
                </tr>`;
      })
      .join("");
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#ef4444" class="py-4 text-xs font-bold italic">SISTEMA NO DISPONIBLE</td></tr>';
  }
}

function setVersion() {
  const el = document.getElementById("version-tag");
  if (el) el.innerText = "Build estable: v2.5.0";
}

document.addEventListener("DOMContentLoaded", () => {
  setVersion();
  loadHomeSessions();
  setInterval(loadHomeSessions, 60000);
});
