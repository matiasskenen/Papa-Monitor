/* ===== friends.js – Gestión de Amigos y Sesiones ===== */

/**
 * Carga el perfil del usuario logueado para saber quién es su amigo fijado.
 */
async function loadMyProfile() {
  try {
    const { data, error } = await sbClient.from("users_profiles").select("*").eq("id", sessionUser.id).maybeSingle();

    if (error) throw error;

    if (data) {
      userProfile = data;
      pinnedFriendId = data.pinned_friend_id;
      // Una vez tenemos el ID fijado, actualizamos la pantalla de Inicio
      if (typeof updateInicioView === "function") {
        updateInicioView();
      }
    }
  } catch (err) {
    console.error("Error al cargar perfil:", err);
  }
}

/**
 * Carga la lista de todos los usuarios (amigos) disponibles para monitorear.
 */
async function loadFriendsData() {
  const list = document.getElementById("friends-list");
  if (!list) return;

  list.innerHTML = `<p class="text-slate-500 animate-pulse">Cargando amigos...</p>`;

  try {
    const { data: profiles, error } = await sbClient
      .from("users_profiles")
      .select("*")
      .neq("id", sessionUser.id) // No mostrarse a uno mismo
      .order("username", { ascending: true });

    if (error) throw error;

    if (!profiles || profiles.length === 0) {
      list.innerHTML = `<p class="text-slate-500">No se encontraron amigos.</p>`;
      return;
    }

    list.innerHTML = profiles
      .map((friend) => {
        const isPinned = friend.id === pinnedFriendId;
        return `
                <div class="glass p-4 rounded-2xl flex justify-between items-center transition-all hover:bg-white/5">
                    <div class="flex items-center gap-4">
                        <div class="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center font-bold text-indigo-400">
                            ${friend.username.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <p class="font-bold text-slate-200">${friend.username}</p>
                            <p class="text-xs text-slate-500">${friend.id.substring(0, 8)}...</p>
                        </div>
                    </div>
                    <button 
                        onclick="pinFriend('${friend.id}')"
                        class="px-4 py-2 rounded-xl text-xs font-bold transition-all ${isPinned ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}"
                    >
                        ${isPinned ? "Fijado" : "Fijar"}
                    </button>
                </div>
            `;
      })
      .join("");
  } catch (err) {
    console.error("Error al cargar amigos:", err);
    list.innerHTML = `<p class="text-rose-400">Error al cargar la lista.</p>`;
  }
}
