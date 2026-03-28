"""Interfaz Tk: panel de control, consola y acciones de instalación."""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime

import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk

from papamonitor import constants
from papamonitor.fortnite_detect import is_fortnite_running
from papamonitor.instance_lock import cerrar_lock
from papamonitor.paths import resource_path
from papamonitor.remote_settings import merge_client_config, monitor_exe_url, resolve_urls
from papamonitor import scheduler
from papamonitor.tray_icon import iniciar_tray
from papamonitor import updater
from papamonitor.versioning import read_bundled_version, remote_version_is_newer


class PapaMonitorApp:
    def __init__(self) -> None:
        self.running = True
        self.is_online = False
        self.client_cfg = merge_client_config()
        self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
        self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
        self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
        self.patterns = list(self.client_cfg["process_substrings"])
        self._loop_ticks = 0

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(f"{constants.APP_NAME} — Panel")
        self.root.configure(bg="#ffffff")

        try:
            self.img_logo = Image.open(resource_path("logo.png"))
            self.photo_logo = ImageTk.PhotoImage(self.img_logo)
            self.root.iconphoto(False, self.photo_logo)
        except OSError:
            self.img_logo = Image.new("RGB", (64, 64), color=(0, 120, 215))

        self.console_visible = tk.BooleanVar(value=False)
        self._console_container: tk.Frame | None = None
        self._tarea_instalada_al_inicio = scheduler.tarea_existe()
        self._unmap_guard = False
        self.root.geometry("520x560" if self._tarea_instalada_al_inicio else "520x360")

        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.ocultar_panel)
        self.root.bind("<Unmap>", self._al_minimizar_ir_a_bandeja)
        self.icon = iniciar_tray(self.img_logo, self.lanzar_panel, self.salir_total)

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        self.lanzar_panel()
        self.root.mainloop()

    # --- UI ---
    def _setup_ui(self) -> None:
        header = tk.Frame(self.root, bg="#0078d7", height=70)
        header.pack(fill="x")
        tk.Label(
            header,
            text="PAPA MONITOR",
            bg="#0078d7",
            fg="white",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=20)

        self.body = tk.Frame(self.root, bg="#ffffff")
        self.body.pack(pady=8, padx=16, fill="x")

        self._console_container = tk.Frame(self.root, bg="#ffffff")

        tk.Label(
            self._console_container,
            text="CONSOLA DEL MONITOR:",
            font=("Segoe UI", 8, "bold"),
            bg="#ffffff",
            fg="#333",
        ).pack(anchor="w")

        self.console = scrolledtext.ScrolledText(
            self._console_container,
            height=14,
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Consolas", 9),
            borderwidth=0,
        )
        self.console.pack(fill="both", expand=True, pady=4)

        footer = tk.Frame(self.root, bg="#f3f3f3")
        footer.pack(fill="x", side="bottom")
        tk.Button(footer, text="Ocultar panel (sigue en bandeja)", bg="#e1e1e1", relief="flat", command=self.ocultar_panel).pack(
            fill="x", padx=4, pady=(2, 0)
        )
        tk.Button(
            footer,
            text="Cerrar monitor por completo",
            bg="#c82333",
            fg="white",
            relief="flat",
            command=self.confirmar_cerrar_monitor,
        ).pack(fill="x", padx=4, pady=(2, 2))

    def log(self, mensaje: str) -> None:
        def _write() -> None:
            ts = datetime.now().strftime("%H:%M:%S")
            self.console.insert(tk.END, f"[{ts}] {mensaje}\n")
            self.console.see(tk.END)

        try:
            self.root.after(0, _write)
        except tk.TclError:
            pass

    def _puede_mostrar_consola(self) -> bool:
        return scheduler.tarea_existe()

    def _toggle_consola_vista(self) -> None:
        if not self._console_container or not self._puede_mostrar_consola():
            return
        if self.console_visible.get():
            self._console_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))
            self.root.update_idletasks()
        else:
            self._console_container.pack_forget()
        self._ajustar_tamano_ventana()

    def toggle_consola(self) -> None:
        self.console_visible.set(not self.console_visible.get())
        self._toggle_consola_vista()

    def dibujar_botones(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

        if updater.es_ejecutable_compilado():
            bloque_act = tk.LabelFrame(self.body, text="Actualización del monitor (.exe)", bg="#ffffff", fg="#333", font=("Segoe UI", 8, "bold"))
            bloque_act.pack(fill="x", pady=(0, 10))
            estado_act = tk.Frame(bloque_act, bg="#ffffff")
            estado_act.pack(fill="x", padx=8, pady=8)
            tk.Label(
                estado_act,
                text="Comprobando versión publicada…",
                bg="#ffffff",
                fg="#555",
                font=("Segoe UI", 9),
            ).pack(anchor="w")
            threading.Thread(target=lambda c=estado_act: self._hilo_comprobar_actualizacion(c), daemon=True).start()

        installed = scheduler.tarea_existe()

        row1 = tk.Frame(self.body, bg="#ffffff")
        row1.pack(fill="x", pady=4)

        if not installed:
            tk.Button(
                row1,
                text="Instalar — inicio con Windows",
                bg="#0078d7",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                height=2,
                command=self.accion_instalar,
            ).pack(fill="x", pady=2)
            hint0 = (
                "El monitor comprobará si la tarea de inicio automático ya existe. "
                "Tras instalar, verás las opciones de actualizar, desinstalar y la consola de actividad."
            )
            tk.Label(self.body, text=hint0, bg="#ffffff", fg="#666", font=("Segoe UI", 8), wraplength=480, justify="left").pack(
                anchor="w", pady=(8, 0)
            )
            return

        tk.Button(
            row1,
            text="Actualizar / reparar tarea programada",
            bg="#0078d7",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            height=2,
            command=self.accion_reparar_tarea,
        ).pack(fill="x", pady=2)

        row2 = tk.Frame(self.body, bg="#ffffff")
        row2.pack(fill="x", pady=4)
        tk.Button(
            row2,
            text="Comprobar actualización del monitor ahora",
            bg="#28a745",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            height=2,
            command=self.accion_buscar_version,
        ).pack(fill="x", pady=2)

        row3 = tk.Frame(self.body, bg="#ffffff")
        row3.pack(fill="x", pady=4)
        tk.Button(
            row3,
            text="Desinstalar tarea y salir",
            bg="#dc3545",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            height=2,
            command=self.accion_desinstalar,
        ).pack(fill="x", pady=2)

        row4 = tk.Frame(self.body, bg="#ffffff")
        row4.pack(fill="x", pady=8)
        tk.Checkbutton(
            row4,
            text="Mostrar consola de actividad",
            variable=self.console_visible,
            command=self._toggle_consola_vista,
            bg="#ffffff",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        hint = (
            "La X y el minimizar ocultan este panel (el monitor sigue en la bandeja). "
            "La consola está oculta hasta que marques la casilla. "
            "Patrones: public-config."
        )
        tk.Label(self.body, text=hint, bg="#ffffff", fg="#666", font=("Segoe UI", 8), wraplength=480, justify="left").pack(
            anchor="w", pady=(6, 0)
        )

    def lanzar_panel(self) -> None:
        self.dibujar_botones()
        self._sincronizar_panel_consola()
        self.root.deiconify()
        self.root.lift()

    def _clear_unmap_guard(self) -> None:
        self._unmap_guard = False

    def ocultar_panel(self) -> None:
        self._unmap_guard = True
        try:
            self.root.withdraw()
        finally:
            self.root.after(200, self._clear_unmap_guard)

    def _al_minimizar_ir_a_bandeja(self, event: tk.Event) -> None:
        """Botón minimizar de Windows: no dejar el proceso colgado minimizado; ir a bandeja."""
        if getattr(event, "widget", None) != self.root:
            return
        if self._unmap_guard:
            return
        try:
            if self.root.state() == "iconic":
                self._unmap_guard = True
                self.root.after(10, self._completar_minimizar_bandeja)
        except tk.TclError:
            pass

    def _completar_minimizar_bandeja(self) -> None:
        try:
            self.root.withdraw()
        except tk.TclError:
            pass
        finally:
            self._unmap_guard = False

    def _ajustar_tamano_ventana(self) -> None:
        if not scheduler.tarea_existe():
            self.root.geometry("520x360")
            return
        if self.console_visible.get() and self._puede_mostrar_consola():
            self.root.geometry("520x720")
        else:
            self.root.geometry("520x560")

    def _sincronizar_panel_consola(self) -> None:
        if self._console_container:
            self._console_container.pack_forget()
        if self._puede_mostrar_consola() and self.console_visible.get():
            self._console_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._ajustar_tamano_ventana()

    def confirmar_cerrar_monitor(self) -> None:
        if messagebox.askyesno(
            "Cerrar monitor",
            "Se detendrá el programa por completo (icono de bandeja incluido).\n\n"
            "Si tenés instalado el inicio con Windows, volverá a abrirse al iniciar sesión o al reiniciar la PC.\n\n"
            "¿Cerrar ahora?",
        ):
            self.salir_total()

    # --- Actualización monitor.exe ---
    def _hilo_comprobar_actualizacion(self, contenedor: tk.Frame) -> None:
        rem = updater.obtener_version_remota(self.version_url)
        cur = read_bundled_version()

        def pintar() -> None:
            for w in contenedor.winfo_children():
                w.destroy()
            if not rem:
                err_l = tk.Label(
                    contenedor,
                    text="No se pudo comprobar la versión en el servidor. Reintentá más tarde.",
                    bg="#f8d7da",
                    fg="#721c24",
                    font=("Segoe UI", 9),
                    wraplength=460,
                    justify="left",
                    padx=10,
                    pady=8,
                )
                err_l.pack(fill="x")
                return
            if not updater.es_ejecutable_compilado():
                tk.Label(
                    contenedor,
                    text=f"Versión instalada (desarrollo): v{cur}. Remoto: v{rem}. La descarga automática solo funciona en monitor.exe.",
                    bg="#e2e3e5",
                    fg="#383d41",
                    font=("Segoe UI", 9),
                    wraplength=460,
                    justify="left",
                    padx=10,
                    pady=8,
                ).pack(fill="x")
                return
            if remote_version_is_newer(rem, cur):
                wrap = tk.Frame(contenedor, bg="#fff3cd", highlightthickness=1, highlightbackground="#ffc107")
                wrap.pack(fill="x")
                tk.Label(
                    wrap,
                    text=f"Hay una actualización del monitor: v{rem} (tenés v{cur}).",
                    bg="#fff3cd",
                    fg="#856404",
                    font=("Segoe UI", 9, "bold"),
                    wraplength=440,
                    justify="left",
                ).pack(anchor="w", padx=10, pady=(8, 2))
                tk.Label(
                    wrap,
                    text="Se descargará monitor.exe desde el sitio y el programa se reiniciará solo.",
                    bg="#fff3cd",
                    fg="#856404",
                    font=("Segoe UI", 8),
                    wraplength=440,
                    justify="left",
                ).pack(anchor="w", padx=10, pady=(0, 6))
                tk.Button(
                    wrap,
                    text="Descargar e instalar actualización",
                    bg="#ff9800",
                    fg="black",
                    font=("Segoe UI", 9, "bold"),
                    command=lambda: self.accion_descargar_actualizacion(rem),
                ).pack(anchor="w", padx=10, pady=(0, 10))
            else:
                tk.Label(
                    contenedor,
                    text=f"Monitor actualizado (v{cur}). La versión publicada es v{rem}.",
                    bg="#d4edda",
                    fg="#155724",
                    font=("Segoe UI", 9),
                    wraplength=460,
                    justify="left",
                    padx=10,
                    pady=8,
                ).pack(fill="x")

        try:
            self.root.after(0, pintar)
        except tk.TclError:
            pass

    def accion_descargar_actualizacion(self, version_remota: str) -> None:
        if not messagebox.askyesno(
            "Actualizar monitor",
            f"Se descargará la versión v{version_remota} y se reiniciará el monitor.\n\n¿Continuar?",
        ):
            return
        self.log("Descargando monitor.exe y preparando reinicio…")
        ok, err = updater.aplicar_actualizacion_monitor(self._exe_update_url)
        if not ok:
            messagebox.showerror("Actualización", f"No se pudo actualizar:\n{err}")
            self.log(f"Error actualización: {err}")
            return
        messagebox.showinfo("Actualización", "Listo. El monitor se cerrará y volverá a abrir en unos segundos.")
        self.salir_total()

    # --- Acciones ---
    def accion_instalar(self) -> None:
        if scheduler.tarea_existe():
            messagebox.showinfo(
                "Ya instalado",
                "La tarea de inicio con Windows ya está configurada.\n"
                "Usá «Actualizar / reparar» o «Desinstalar» si la necesitás cambiar.",
            )
            self.dibujar_botones()
            self._sincronizar_panel_consola()
            return
        ok, msg = scheduler.crear_tarea_inicio()
        if ok:
            self.dibujar_botones()
            self._sincronizar_panel_consola()
            self.log("Tarea programada creada (inicio con Windows).")
            self.log(f"API: {self.api_url} | sondeo: {self.poll_interval}s | patrones: {', '.join(self.patterns)}")
            messagebox.showinfo("Listo", "Instalación de inicio automático correcta.")
        else:
            if self._puede_mostrar_consola():
                self.log(f"Error al crear tarea: {msg}")
            else:
                messagebox.showerror("Error", f"No se pudo crear la tarea:\n{msg}")

    def accion_reparar_tarea(self) -> None:
        scheduler.eliminar_tarea()
        ok, msg = scheduler.crear_tarea_inicio()
        if ok:
            self.log("Tarea reprogramada correctamente.")
            messagebox.showinfo("Listo", "Tarea actualizada / reparada.")
            self.dibujar_botones()
            self._sincronizar_panel_consola()
        else:
            self.log(f"Error al reprogramar: {msg}")

    def accion_buscar_version(self) -> None:
        try:
            current = read_bundled_version()
            remote = updater.obtener_version_remota(self.version_url)
            if not remote:
                messagebox.showwarning("Actualización", "No se pudo leer la versión del servidor.")
                return
            if remote_version_is_newer(remote, current):
                if updater.es_ejecutable_compilado():
                    if messagebox.askyesno(
                        "Actualización disponible",
                        f"Remoto: v{remote} · Instalada: v{current}.\n\n"
                        "¿Descargar e instalar la nueva versión del monitor ahora?",
                    ):
                        self.accion_descargar_actualizacion(remote)
                else:
                    messagebox.showinfo(
                        "Actualización",
                        f"Hay v{remote} publicada (vos: v{current}). En el .exe compilado podés instalarla con un clic; en desarrollo descargala del sitio.",
                    )
            else:
                if self._puede_mostrar_consola():
                    self.log(f"Versión actual: v{current}. Publicada: v{remote}. Estás al día.")
                else:
                    messagebox.showinfo("Actualización", f"Estás al día (v{current}). Publicada: v{remote}.")
        except Exception as e:
            if self._puede_mostrar_consola():
                self.log(f"Error al buscar versión: {e}")
            else:
                messagebox.showerror("Actualización", str(e))

    def accion_desinstalar(self) -> None:
        if not messagebox.askyesno("Confirmar", "¿Eliminar la tarea programada y cerrar el monitor?"):
            return
        ok, msg = scheduler.eliminar_tarea()
        if not ok and "no es compatible" not in msg.lower() and msg:
            self.log(f"Aviso al borrar tarea: {msg}")
        self.salir_total()

    # --- Monitor ---
    def _monitor_loop(self) -> None:
        if self._puede_mostrar_consola():
            self.root.after(
                0,
                lambda: self.log(
                    f"API: {self.api_url} | sondeo: {self.poll_interval}s | patrones: {', '.join(self.patterns)}"
                ),
            )
        while self.running:
            try:
                self._loop_ticks += 1
                if self._loop_ticks % 90 == 0:
                    self.client_cfg = merge_client_config()
                    self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
                    self._exe_update_url = monitor_exe_url(self.client_cfg["api_base"])
                    self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
                    self.patterns = list(self.client_cfg["process_substrings"])
                    if self._puede_mostrar_consola():
                        self.log("(Config remota refrescada)")

                encontrado = is_fortnite_running(self.patterns, constants.PROCESS_NAME_EXCLUDE_SUBSTRINGS)

                if encontrado:
                    if not self.is_online:
                        self.log("Fortnite detectado. Enviando ONLINE…")
                        self.is_online = True
                    r = requests.post(self.api_url, json={"is_online": True}, timeout=15)
                    if r.status_code >= 400:
                        self.log(f"POST ONLINE falló ({r.status_code}): {(r.text or '')[:180]}")
                elif self.is_online:
                    self.log("Juego cerrado. Enviando OFFLINE…")
                    self.is_online = False
                    r = requests.post(self.api_url, json={"is_online": False}, timeout=15)
                    if r.status_code >= 400:
                        self.log(f"POST OFFLINE falló ({r.status_code}): {(r.text or '')[:180]}")

            except Exception as e:
                self.log(f"Error en monitor: {e}")

            time.sleep(max(10, self.poll_interval))

    def salir_total(self) -> None:
        self.running = False
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass
        cerrar_lock()
        os._exit(0)
