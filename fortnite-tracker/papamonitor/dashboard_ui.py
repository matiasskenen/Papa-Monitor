"""Interfaz PyWebView: panel de control, consola y acciones de instalación."""

from __future__ import annotations

import os
import sys
import threading
import time
import json
import webbrowser
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests
import webview

from papamonitor import constants
from papamonitor.fortnite_detect import is_fortnite_running
from papamonitor.instance_lock import cerrar_lock
from papamonitor.paths import resource_path
from papamonitor.remote_settings import merge_client_config, monitor_exe_url, resolve_urls
from papamonitor import scheduler
from papamonitor.tray_icon import iniciar_tray
from papamonitor import updater
from papamonitor.versioning import read_bundled_version, remote_version_is_newer

class Api:
    def __init__(self, app: PapaMonitorApp):
        self.app = app

    def loaded(self):
        self.app.on_ui_ready()

    def minimize(self):
        self.app.ocultar_panel()

    def kill(self):
        self.app.salir_total()

    def reparar_tarea(self):
        self.app.accion_reparar_tarea()

    def check_updates(self):
        self.app.accion_buscar_version()

    def desinstalar_tarea(self):
        self.app.accion_desinstalar_tarea()

    def toggle_emails(self, enabled: bool):
        # Deprecado: emails siempre activos en el servidor
        self.app.log("Emails siempre activos en el servidor (toggle deshabilitado).", "SYS", "neutral")

    def login_google(self):
        self.app.accion_login_google()

    def logout(self):
        self.app.accion_logout()

    def get_stats(self):
        """Devuelve estadísticas locales para los gráficos."""
        return self.app.read_local_stats()

    def do_auto_update(self):
        # Llamado por el botón "Instalar Ahora"
        self.app.forzar_actualizacion()

    def save_token(self, token: str):
        self.app.save_jwt_token(token)


class PapaMonitorApp:
    def __init__(self) -> None:
        self.running = True
        self.is_online = False
        self.session_start_iso = None
        
        # Cargar sesión persistente si existe
        self.session_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd(), "session.json")
        self.jwt_token = self._load_session()
        
        # Valores por defecto para abrir la interfaz instantáneamente.
        # El loop de fondo traerá la configuración real de inmediato.
        self.client_cfg = {"api_base": constants.DEFAULT_API_BASE, "poll_interval_seconds": 10, "process_substrings": constants.DEFAULT_PROCESS_SUBSTRINGS}
        self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
        self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
        self.poll_interval = 10
        self.patterns = list(self.client_cfg["process_substrings"])
        self._loop_ticks = 0
        self.window = None

        self.img_logo = self._load_logo()
        self.icon = iniciar_tray(self.img_logo, self.lanzar_panel, self.ocultar_panel, self.salir_total)
        self.api_instance = Api(self)

        # Iniciar interface de forma segura
        self.window = webview.create_window(
            constants.APP_NAME,
            resource_path("papamonitor/dashboard.html"),
            width=940,
            height=700,
            js_api=self.api_instance,
            min_size=(900, 640),
            background_color="#020617",
        )
        self.window.events.shown += self.on_window_shown
        self.window.events.loaded += self.on_url_loaded
        self.window.events.closing += self._on_window_closing

    def _load_logo(self):
        from PIL import Image
        try:
            return Image.open(resource_path("logo.png"))
        except Exception:
            return Image.new("RGB", (64, 64), color=(0, 120, 215))

    def run(self):
        # Bloquea el thread principal e inicia el loop de eventos de la UI
        webview.start(debug=True if "--debug" in sys.argv else False)

    def on_ui_ready(self):
        """Llamado desde JS cuando el DOM y pywebview están listos."""
        threading.Thread(target=self._initial_setup_task, daemon=True).start()

    def _initial_setup_task(self):
        """Tarea pesada de inicialización post-show para no bloquear el inicio."""
        try:
            self._update_boot_progress(20, "Cargando configuración...")
            self.client_cfg = merge_client_config()
            self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
            self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
            self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
            self.patterns = list(self.client_cfg["process_substrings"])
            
            self._update_boot_progress(50, "Verificando actualizaciones...")
            self.on_ui_ready_sync() # Carga el resto de cosas visuales
            
            self._update_boot_progress(80, "Sincronizando estado...")
            self.sync_state_to_ui()
            
            self._update_boot_progress(100, "Listo")
            
            # Iniciar el monitor loop ahora que todo está configurado
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            
        except Exception as e:
            self.log(f"Error en setup inicial: {e}", "ERR", "red")
            self._update_boot_progress(100, "Error")

    def _update_boot_progress(self, pct, text):
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.updateBootProgress) window.updateBootProgress({pct}, '{text}')")
            except Exception:
                pass

    def _save_session(self, token: str):
        try:
            with open(self.session_path, "w") as f:
                json.dump({"jwt": token}, f)
        except Exception as e:
            self.log(f"Error guardando sesión: {e}", "SYS", "red")

    def _load_session(self) -> str | None:
        if os.path.exists(self.session_path):
            try:
                with open(self.session_path, "r") as f:
                    data = json.load(f)
                    return data.get("jwt")
            except Exception:
                pass
        return None

    def on_window_shown(self):
        self.log("Consola iniciada.", "SYS", "neutral")
        if self.jwt_token:
            self.sync_state_to_ui()

    def on_url_loaded(self):
        if not self.window: return
        url = self.window.get_current_url()
        # Mantenemos este fallback por si acaso, pero el flujo principal será via local_server
        if url and "access_token=" in url:
            self._process_token_from_url(url)

    def _process_token_from_url(self, url: str):
        try:
            # El fragmento viene después de #
            fragment = url.split("#")[1] if "#" in url else ""
            params = parse_qs(fragment)
            token = params.get("access_token", [None])[0]
            if token:
                self.jwt_token = token
                self._save_session(token)
                self.log("¡Sesión de Google vinculada exitosamente!", "SYS", "green")
                # Volver al dashboard local o refrescar
                if self.window:
                    self.window.load_url(resource_path("papamonitor/dashboard.html"))
                self.sync_state_to_ui()
                return True
        except Exception as e:
            self.log(f"Error procesando token: {e}", "ERR", "red")
        return False

    # --- UI Callbacks ---
    def on_ui_ready_sync(self):
        self.window.evaluate_js(f"setVersion('{read_bundled_version()}')")
        
        # Enviar fecha de última actualización
        try:
            mtime = os.path.getmtime(sys.executable)
            dt = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            dt = "Desconocido"
            
        self.window.evaluate_js(f"setLastUpdateDate('{dt}')")
        
        is_inst = "true" if scheduler.tarea_existe() else "false"
        self.window.evaluate_js(f"setInstallState({is_inst})")
        
        self.log("Consola iniciada.", "SYS", "neutral")
        self.sync_state_to_ui()
        # Emails siempre activos en servidor, no hay toggle que cargar

    def sync_state_to_ui(self):
        if not self.window: return
        is_logged = "true" if self.jwt_token else "false"
        js_cmd = f"setSystemState({'true' if self.is_online else 'false'}, '{self.session_start_iso or ''}', {is_logged})"
        try:
            self.window.evaluate_js(js_cmd)
        except Exception:
            pass

    def log(self, mensaje: str, tag: str = "SYS", color: str = "neutral") -> None:
        if not self.window: return
        ts = datetime.now().strftime("%H:%M:%S")
        safe_msg = str(mensaje).replace("'", "\\'").replace("\n", " ")
        try:
            self.window.evaluate_js(f"addLog('{ts}', '{tag}', '{color}', '{safe_msg}')")
        except Exception:
            pass

    def lanzar_panel(self) -> None:
        if self.window:
            self.window.show()
            self.window.restore()

    def ocultar_panel(self) -> None:
        if self.window:
            self.window.hide()

    def _on_window_closing(self) -> bool:
        """Intercepta el evento de cierre: oculta la ventana en lugar de cerrarla."""
        self.ocultar_panel()
        return False  # False = cancelar el cierre real

    def _on_window_closed(self) -> None:
        """Por si acaso el cierre ocurre igual (ej: salir_total). No hace nada extra."""
        pass

    def read_local_stats(self):
        import json
        # Usar LOCALAPPDATA para persistencia si es posible, sino el dir del exe
        base_dir = os.environ.get('LOCALAPPDATA', os.getcwd())
        app_dir = os.path.join(base_dir, "PapaMonitor")
        if not os.path.exists(app_dir): os.makedirs(app_dir, exist_ok=True)
        path = os.path.join(app_dir, "sessions_v1.json")
        
        if not os.path.exists(path):
            return {"total_minutes": 0, "history": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"total_minutes": 0, "history": {}}

    def save_local_session(self, minutes):
        import json
        from datetime import date
        base_dir = os.environ.get('LOCALAPPDATA', os.getcwd())
        app_dir = os.path.join(base_dir, "PapaMonitor")
        if not os.path.exists(app_dir): os.makedirs(app_dir, exist_ok=True)
        path = os.path.join(app_dir, "sessions_v1.json")
        
        data = self.read_local_stats()
        data["total_minutes"] = data.get("total_minutes", 0) + minutes
        
        history = data.get("history", {})
        today = date.today().isoformat()
        history[today] = history.get(today, 0) + minutes
        data["history"] = history
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

    def salir_total(self) -> None:
        self.running = False
        try:
            if getattr(self, "icon", None):
                self.icon.stop()
        except Exception:
            pass
        cerrar_lock()
        
        # Forzamos cierre a nivel de sistema inmediatamente
        os._exit(0)

    def load_jwt_token(self):
        base_dir = os.environ.get('LOCALAPPDATA', os.getcwd())
        app_dir = os.path.join(base_dir, "PapaMonitor")
        path = os.path.join(app_dir, "token.jwt")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return f.read().strip()
            except:
                pass
        return ""

    def save_jwt_token(self, token: str):
        base_dir = os.environ.get('LOCALAPPDATA', os.getcwd())
        app_dir = os.path.join(base_dir, "PapaMonitor")
        if not os.path.exists(app_dir): os.makedirs(app_dir, exist_ok=True)
        path = os.path.join(app_dir, "token.jwt")
        try:
            with open(path, "w") as f:
                f.write(token.strip())
            self.jwt_token = token.strip()
            self.log("Token JWT guardado exitosamente.", "SYS", "green")
            # Refresca la configuración si es necesario
        except Exception as e:
            self.log(f"Error guardando token: {e}", "ERR", "red")

    # --- Acciones (Botones) ---
    def accion_reparar_tarea(self) -> None:
        scheduler.eliminar_tarea()
        ok, msg = scheduler.crear_tarea_inicio()
        if ok:
            self.log("Tarea de inicio configurada con éxito.", "SYS", "green")
            if self.window:
                self.window.evaluate_js("setInstallState(true)")
        else:
            self.log(f"Error configurando tarea: {msg}", "ERR", "red")

    def accion_desinstalar_tarea(self) -> None:
        ok, msg = scheduler.eliminar_tarea()
        if ok or "no se puede encontrar" in msg.lower() or "no pudo" in msg.lower():
            self.log("Tarea programada de Windows desinstalada.", "SYS", "green")
            self.log("Cerrando programa por completo...", "SYS", "neutral")
            
            # Matamos el programa instantáneamente ya que la animación JS ya transcurrió
            self.salir_total()
        else:
            self.log(f"Fallo al desinstalar: {msg}", "ERR", "red")

    def accion_buscar_version(self) -> None:
        if self.window:
            self.window.evaluate_js("scrollLogsView()")
            
        try:
            current = read_bundled_version()
            remote = updater.obtener_version_remota(self.version_url)
            if not remote:
                self.log("No se pudo leer la versión del servidor.", "ERR", "red")
                return
            if remote_version_is_newer(remote, current):
                self.log(f"¡Actualización v{remote} disponible!", "SYS", "blue")
                if self.window:
                    self.window.evaluate_js(f"showUpdateBanner('v{remote}', true)")
            else:
                self.log(f"Estás al día (v{current}).", "SYS", "green")
        except Exception as e:
            self.log(f"Error comprobando actualizaciones: {e}", "ERR", "red")
            


    def forzar_actualizacion(self):
        remote = updater.obtener_version_remota(self.version_url)
        if remote:
            self._do_auto_update(remote)
            
    def _update_progress_ui(self, pct: int) -> None:
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.updateDownloadProgress) window.updateDownloadProgress({pct})")
            except Exception:
                pass

    def _do_auto_update(self, rem_ver: str):
        if getattr(self, "icon", None):
            try:
                self.icon.notify(
                    f"Descargando versión {rem_ver} automáticamente. El monitor se reiniciará.",
                    title="Actualización"
                )
            except Exception:
                pass
                
        def progress_tracker(pct):
            if self.window:
                try:
                    self.window.evaluate_js(f"if(window.updateDownloadProgress) window.updateDownloadProgress({pct})")
                except Exception:
                    pass

        ok, err = updater.aplicar_actualizacion_monitor(self._exe_update_url, progress_callback=progress_tracker)
        if ok:
            self.log("Instalador preparado, reiniciando...", "SYS", "green")
            if self.window:
                try:
                    self.window.evaluate_js("if(window.updateDownloadProgress) window.updateDownloadProgress(100, true)")
                except Exception:
                    pass
            time.sleep(1.5) # Esperamos a que la animacion termine
            self.salir_total()
        else:
            self.log(f"Auto-update falló: {err}", "ERR", "red")
            if self.window:
                try:
                    self.window.evaluate_js(f"if(window.resetDownloadUI) window.resetDownloadUI('{err}')")
                except Exception:
                    pass


    def _monitor_loop(self) -> None:
        while self.running:
            try:
                self._loop_ticks += 1
                if self._loop_ticks == 1 or self._loop_ticks % 90 == 0:
                    self.client_cfg = merge_client_config()
                    self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
                    self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
                    self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
                    self.patterns = list(self.client_cfg["process_substrings"])
                    
                    if self._loop_ticks == 1:
                        self.log(f"API Listando en: {self.api_url}", "NET", "blue")
                    else:
                        self.log("Configuración remota refrescada.", "SYS", "neutral")

                    if updater.es_ejecutable_compilado():
                        try:
                            rem_ver = updater.obtener_version_remota(self.version_url)
                            cur_ver = read_bundled_version()
                            if rem_ver and remote_version_is_newer(rem_ver, cur_ver):
                                self.log(f"Auto-update: v{rem_ver} detectada. Iniciando...", "SYS", "blue")
                                if self.window:
                                    self.window.evaluate_js(f"showUpdateBanner('v{rem_ver}', true)")
                                self._do_auto_update(rem_ver)
                        except Exception as e:
                            self.log(f"Error auto-update: {e}", "ERR", "red")

                encontrado = is_fortnite_running(self.patterns, constants.PROCESS_NAME_EXCLUDE_SUBSTRINGS)

                if encontrado:
                    if not self.is_online:
                        self.log("Fortnite.exe detectado en CPU.", "DET", "green")
                        self.is_online = True
                        self.session_start_iso = datetime.utcnow().isoformat() + "Z"
                        self.sync_state_to_ui()
                    try:
                        headers = {}
                        if self.jwt_token:
                            headers["Authorization"] = f"Bearer {self.jwt_token}"
                        r = requests.post(self.api_url, json={"is_online": True}, headers=headers, timeout=15)
                        if r.status_code >= 400:
                            self.log(f"POST ONLINE falló ({r.status_code}): {r.text}", "NET", "red")
                    except Exception as net_err:
                        self.log(f"Red: no se pudo notificar ONLINE: {net_err}", "NET", "red")
                elif self.is_online:
                    # Guardar estadísticas locales
                    try:
                        if self.session_start_iso:
                            # Python 3.11+ maneja Z, pero para versiones anteriores:
                            parsed_start = self.session_start_iso.rstrip("Z")
                            start_dt = datetime.fromisoformat(parsed_start)
                            diff = datetime.utcnow() - start_dt
                            mins = max(1, int(diff.total_seconds() / 60))
                            self.save_local_session(mins)
                            self.log(f"Estadísticas: +{mins}m guardados localmente.", "SYS", "blue")
                    except Exception as se:
                        self.log(f"Error stats: {se}", "ERR", "red")

                    self.log("Juego cerrado. Sesión finalizada.", "SYS", "neutral")
                    self.is_online = False
                    self.session_start_iso = None
                    self.sync_state_to_ui()
                    try:
                        headers = {}
                        if self.jwt_token:
                            headers["Authorization"] = f"Bearer {self.jwt_token}"
                        r = requests.post(self.api_url, json={"is_online": False}, headers=headers, timeout=15)
                        if r.status_code >= 400:
                            self.log(f"POST OFFLINE falló ({r.status_code}): {r.text}", "NET", "red")
                    except Exception as net_err:
                        self.log(f"Red: no se pudo notificar OFFLINE: {net_err}", "NET", "red")

            except Exception as e:
                self.log(f"Error en monitor loop: {e}", "ERR", "red")

            time.sleep(max(10, self.poll_interval))

    def accion_login_google(self):
        if self.window:
            self.window.evaluate_js("setLoginLoading(true)")

        if not self.client_cfg or not self.client_cfg.get("supabase_url"):
            # Si entramos aquí, el setup inicial falló o tardó
            self.client_cfg = merge_client_config()
            
        sb_url = self.client_cfg.get("supabase_url")
        api_base = self.client_cfg.get("api_base", "https://papa-monitor.vercel.app")

        if sb_url:
            self.log("Generando sesión de login...", "SYS", "blue")
            try:
                # 1. Crear sesión en el backend
                r = requests.get(f"{api_base}/api/auth/session/create", timeout=10)
                if r.status_code != 200:
                    raise Exception(f"Servidor respondió con error {r.status_code}. ¿Desplegaste los cambios en Vercel?")
                
                try:
                    resp = r.json()
                except Exception:
                    raise Exception("El servidor no devolvió una respuesta válida. Verifica tu despliegue en Vercel.")

                sid = resp.get("session_id")
                if not sid: raise Exception("No se obtuvo Session ID del servidor")

                # 2. Configurar redirect hacia nuestra web con el sid
                redirect = f"{api_base}?auth_sid={sid}"
                auth_url = f"{sb_url}/auth/v1/authorize?provider=google&redirect_to={redirect}"
                
                # 3. Abrir navegador
                webbrowser.open(auth_url)
                self.log("Esperando login en Chrome...", "SYS", "blue")

                # 4. Iniciar hilo de polling
                threading.Thread(target=self._poll_for_session, args=(sid, api_base), daemon=True).start()
                
            except Exception as e:
                err_msg = str(e).replace("'", "\\'").replace("\n", " ")
                self.log(f"Error iniciando login: {err_msg}", "ERR", "red")
                if self.window:
                    self.window.evaluate_js(f"setLoginError('{err_msg}')")
        else:
            self.log("Error: No se pudo conectar con Supabase.", "ERR", "red")
            if self.window:
                self.window.evaluate_js("setLoginError('No se pudo obtener configuración desde el servidor. Revisa tu conexión.')")

    def _poll_for_session(self, sid, api_base):
        max_attempts = 60 # 2 minutos (un intento cada 2 segundos)
        self.log(f"Iniciando sondeo de sesión {sid[:8]}...", "SYS", "blue")
        
        try:
            for i in range(max_attempts):
                if not self.running: break
                
                try:
                    r = requests.get(f"{api_base}/api/auth/session/poll?session_id={sid}", timeout=5)
                    if r.status_code == 200:
                        resp = r.json()
                        token = resp.get("token")
                        if token:
                            self.jwt_token = token
                            self._save_session(token)
                            self.log("¡Sesión vinculada!", "SYS", "green")
                            if self.window:
                                self.window.evaluate_js("setLoginLoading(false)")
                            # Forzar recarga o sincronización para ocultar el overlay
                            self.sync_state_to_ui()
                            # Intentar curar perfil si es nuevo
                            threading.Thread(target=self._heal_profile_silently, daemon=True).start()
                            return
                        
                        if resp.get("error"):
                            self.log(f"Error en sondeo: {resp.get('error')}", "ERR", "red")
                            if self.window:
                                self.window.evaluate_js(f"setLoginError('Error: {resp.get('error')}')")
                            return
                    else:
                        # Silencioso a menos que sea error crítico
                        pass
                except Exception:
                    pass
                
                time.sleep(2)
            
            self.log("El tiempo de espera para el login ha expirado.", "ERR", "red")
            if self.window:
                self.window.evaluate_js("setLoginError('Tiempo de espera agotado. Reintenta.')")
                
        finally:
            # Asegurar que el spinner se quite si salimos por cualquier motivo (éxito o fallo)
            if self.window and not self.jwt_token:
                self.window.evaluate_js("setLoginLoading(false)")

    def _heal_profile_silently(self):
        if not self.jwt_token or not self.client_cfg: return
        try:
            api_base = self.client_cfg.get("api_base")
            if api_base:
                url = f"{api_base}/api/heal-profile"
                requests.post(url, headers={"Authorization": f"Bearer {self.jwt_token}"}, timeout=10)
        except Exception:
            pass

    def _start_local_callback_server(self, port):
        pass

    def accion_logout(self):
        self.jwt_token = None
        if os.path.exists(self.session_path):
            os.remove(self.session_path)
        self.log("Sesión cerrada.", "SYS", "neutral")
        self.window.load_url(resource_path("papamonitor/dashboard.html"))

