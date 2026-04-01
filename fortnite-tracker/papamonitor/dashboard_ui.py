"""Interfaz PyWebView: panel de control, consola y acciones de instalación."""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime

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

    def do_auto_update(self):
        # Llamado por el botón "Instalar Ahora"
        self.app.forzar_actualizacion()


class PapaMonitorApp:
    def __init__(self) -> None:
        self.running = True
        self.is_online = False
        self.session_start_iso = None
        
        # Valores por defecto para abrir la interfaz instantáneamente.
        # El loop de fondo traerá la configuración real de inmediato.
        self.client_cfg = {"api_base": constants.DEFAULT_API_BASE, "poll_interval_seconds": 10, "process_substrings": constants.DEFAULT_PROCESS_SUBSTRINGS}
        self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
        self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
        self.poll_interval = 10
        self.patterns = list(self.client_cfg["process_substrings"])
        self._loop_ticks = 0
        self.window = None

        from PIL import Image
        try:
            self.img_logo = Image.open(resource_path("logo.png"))
        except OSError:
            self.img_logo = Image.new("RGB", (64, 64), color=(0, 120, 215))

        self.icon = iniciar_tray(self.img_logo, self.lanzar_panel, self.ocultar_panel, self.salir_total)
        self.api_instance = Api(self)

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        
        # Iniciar interface
        try:
            html_path = resource_path("papamonitor/dashboard.html")
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()
        except OSError:
            html_content = "<h1>Error: HTML no encontrado</h1>"

        start_minimized = "--start-minimized" in sys.argv

        self.window = webview.create_window(
            title=f"{constants.APP_NAME} — Panel",
            html=html_content,
            js_api=self.api_instance,
            width=900,
            height=650,
            frameless=True,
            easy_drag=True,
            background_color='#060608',
            hidden=start_minimized,
        )

        # Interceptar el cierre de ventana para minimizar en lugar de cerrar
        self.window.events.closed += self._on_window_closed
        self.window.events.closing += self._on_window_closing

        # Bloquea el thread principal
        webview.start(debug=False)

    # --- UI Callbacks ---
    def on_ui_ready(self):
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
        js_cmd = f"setSystemState({'true' if self.is_online else 'false'}, '{self.session_start_iso or ''}')"
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
                        r = requests.post(self.api_url, json={"is_online": True}, timeout=15)
                        if r.status_code >= 400:
                            self.log(f"POST ONLINE falló ({r.status_code})", "NET", "red")
                    except Exception as net_err:
                        self.log(f"Red: no se pudo notificar ONLINE: {net_err}", "NET", "red")
                elif self.is_online:
                    self.log("Juego cerrado. Sesión finalizada.", "SYS", "neutral")
                    self.is_online = False
                    self.session_start_iso = None
                    self.sync_state_to_ui()
                    try:
                        r = requests.post(self.api_url, json={"is_online": False}, timeout=15)
                        if r.status_code >= 400:
                            self.log(f"POST OFFLINE falló ({r.status_code})", "NET", "red")
                    except Exception as net_err:
                        self.log(f"Red: no se pudo notificar OFFLINE: {net_err}", "NET", "red")

            except Exception as e:
                self.log(f"Error en monitor loop: {e}", "ERR", "red")

            time.sleep(max(10, self.poll_interval))

