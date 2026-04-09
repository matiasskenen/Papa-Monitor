/* ===== friends.js – Lógica de Amigos y Sesiones ===== */

async function loadMyProfile() {
  const { data, error } = await sbClient.from("users_profiles").select("*").eq("id", sessionUser.id).maybeSingle();

  if (data) {
    userProfile = data;
    pinnedFriendId = data.pinned_friend_id;
    // Esta función vive en monitor.js
    if (typeof updateInicioView === "function") updateInicioView();
  }
}

async function loadFriendsData() {
  const list = document.getElementById("friends-list");
  if (!list) return;

  list.innerHTML = `<p class="text-slate-500 animate-pulse">Cargando amigos...</p>`;

  const { data, error } = await sbClient.from("users_profiles").select("*").neq("id", sessionUser.id);

  if (error || !data) {
    list.innerHTML = `<p class="text-rose-400">Error al cargar lista.</p>`;
    return;
  }

  list.innerHTML = data
    .map(
      (friend) => `
    <div class="glass p-4 rounded-2xl flex justify-between items-center">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center font-bold text-indigo-400">
                ${friend.display_name?.charAt(0) || "U"}
            </div>
            <span>${friend.display_name || "Usuario"}</span>
        </div>
        <button onclick="pinFriend('${friend.id}')" class="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600 text-indigo-400 hover:text-white rounded-xl text-sm transition-all">
            ${pinnedFriendId === friend.id ? "Fijado" : "Fijar"}
        </button>
    </div>
  `,
    )
    .join("");
}

async function pinFriend(friendId) {
  const { error } = await sbClient.from("users_profiles").update({ pinned_friend_id: friendId }).eq("id", sessionUser.id);

  if (!error) {
    pinnedFriendId = friendId;
    alert("Amigo fijado correctamente");
    loadMyProfile(); // Recargar perfil y vista
  }
}

async function loadAppStatusData() {
  if (!pinnedFriendId) return;
  const { data: sessions } = await sbClient.from("sessions").select("*").eq("user_id", pinnedFriendId).order("start_time", { ascending: false }).limit(5);

  const list = document.getElementById("last-sessions-list");
  if (sessions && list) {
    list.innerHTML = sessions
      .map(
        (s) => `
      <div class="glass p-4 rounded-2xl flex justify-between items-center mb-2 border border-white/5">
          <span>Sesión ${fmt(s.start_time)}</span>
          <span class="font-bold ${s.is_active ? "text-emerald-400" : "text-indigo-400"}">
            ${s.is_active ? "En vivo" : getDur(s.start_time, s.end_time, s.is_active)}
          </span>
      </div>
    `,
      )
      .join("");
  }
}
