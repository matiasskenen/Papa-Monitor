/* ===== friends.js – Lógica de Amigos y Sesiones ===== */
async function loadMyProfile() {
  const { data } = await sbClient.from("users_profiles").select("*").eq("id", sessionUser.id).maybeSingle();
  if (data) {
    userProfile = data;
    pinnedFriendId = data.pinned_friend_id;
    updateInicioView();
  }
}

async function loadAppStatusData() {
  if (!pinnedFriendId) return;
  const { data: sessions } = await sbClient.from("sessions").select("*").eq("user_id", pinnedFriendId).order("start_time", { ascending: false }).limit(3);

  const list = document.getElementById("last-sessions-list");
  if (sessions && sessions.length > 0) {
    list.innerHTML = sessions
      .map(
        (s) => `
            <div class="glass p-4 rounded-2xl flex justify-between items-center mb-2">
                <span>Sesión ${fmt(s.start_time, { hour: "2-digit", minute: "2-digit" })}</span>
                <span class="font-bold text-indigo-400">${getDur(s.start_time, s.end_time, s.is_active)}</span>
            </div>
        `,
      )
      .join("");
  }
}
