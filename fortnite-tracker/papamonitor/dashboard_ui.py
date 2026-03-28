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
from papamonitor.remote_settings import merge_client_config, resolve_urls
from papamonitor import scheduler
from papamonitor.tray_icon import iniciar_tray
from papamonitor.versioning import read_bundled_version, remote_version_is_newer


class PapaMonitorApp:
    def __init__(self) -> None:
        self.running = True
        self.is_online = False
        self.client_cfg = merge_client_config()
        self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
        self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
        self.patterns = list(self.client_cfg["process_substrings"])
        self._loop_ticks = 0

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(f"{constants.APP_NAME} — Panel")
        self.root.geometry("520x680")
        self.root.configure(bg="#ffffff")

        try:
            self.img_logo = Image.open(resource_path("logo.png"))
            self.photo_logo = ImageTk.PhotoImage(self.img_logo)
            self.root.iconphoto(False, self.photo_logo)
        except OSError:
            self.img_logo = Image.new("RGB", (64, 64), color=(0, 120, 215))

        self.console_visible = tk.BooleanVar(value=True)
        self._console_container: tk.Frame | None = None

        self._setup_ui()
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
            fill="x", padx=4, pady=2
        )

    def log(self, mensaje: str) -> None:
        def _write() -> None:
            ts = datetime.now().strftime("%H:%M:%S")
            self.console.insert(tk.END, f"[{ts}] {mensaje}\n")
            self.console.see(tk.END)

        try:
            self.root.after(0, _write)
        except tk.TclError:
            pass

    def _toggle_consola_vista(self) -> None:
        if not self._console_container:
            return
        if self.console_visible.get():
            self._console_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))
            self.root.update_idletasks()
        else:
            self._console_container.pack_forget()

    def toggle_consola(self) -> None:
        self.console_visible.set(not self.console_visible.get())
        self._toggle_consola_vista()

    def dibujar_botones(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

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
        else:
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
            text="Buscar actualización (versión web)",
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
            "Tras instalar la tarea, el monitor sigue en la bandeja. "
            "Patrones de proceso se cargan del servidor (public-config)."
        )
        tk.Label(self.body, text=hint, bg="#ffffff", fg="#666", font=("Segoe UI", 8), wraplength=480, justify="left").pack(
            anchor="w", pady=(6, 0)
        )

    def lanzar_panel(self) -> None:
        self.dibujar_botones()
        self._toggle_consola_vista()
        self.root.deiconify()
        self.root.lift()

    def ocultar_panel(self) -> None:
        self.root.withdraw()

    # --- Acciones ---
    def accion_instalar(self) -> None:
        ok, msg = scheduler.crear_tarea_inicio()
        if ok:
            self.log("Tarea programada creada (inicio con Windows).")
            messagebox.showinfo("Listo", "Instalación de inicio automático correcta.")
            self.dibujar_botones()
        else:
            self.log(f"Error al crear tarea: {msg}")

    def accion_reparar_tarea(self) -> None:
        scheduler.eliminar_tarea()
        ok, msg = scheduler.crear_tarea_inicio()
        if ok:
            self.log("Tarea reprogramada correctamente.")
            messagebox.showinfo("Listo", "Tarea actualizada / reparada.")
            self.dibujar_botones()
        else:
            self.log(f"Error al reprogramar: {msg}")

    def accion_buscar_version(self) -> None:
        try:
            current = read_bundled_version()
            r = requests.get(self.version_url, timeout=8)
            remote = (r.text or "").strip()
            if remote and remote_version_is_newer(remote, current):
                messagebox.showinfo(
                    "Actualización",
                    f"Hay una versión más nueva en la web (remoto: v{remote}, tuyo: v{current}).\n"
                    f"Descargá desde el sitio PapaMonitor.",
                )
            else:
                self.log(f"Versión actual: v{current}. Remoto: v{remote or '—'}. Estás al día.")
        except Exception as e:
            self.log(f"Error al buscar versión: {e}")

    def accion_desinstalar(self) -> None:
        if not messagebox.askyesno("Confirmar", "¿Eliminar la tarea programada y cerrar el monitor?"):
            return
        ok, msg = scheduler.eliminar_tarea()
        if not ok and "no es compatible" not in msg.lower() and msg:
            self.log(f"Aviso al borrar tarea: {msg}")
        self.salir_total()

    # --- Monitor ---
    def _monitor_loop(self) -> None:
        self.log(f"API: {self.api_url} | sondeo: {self.poll_interval}s | patrones: {', '.join(self.patterns)}")
        while self.running:
            try:
                self._loop_ticks += 1
                if self._loop_ticks % 90 == 0:
                    self.client_cfg = merge_client_config()
                    self.api_url, self.version_url = resolve_urls(self.client_cfg["api_base"])
                    self.poll_interval = int(self.client_cfg["poll_interval_seconds"])
                    self.patterns = list(self.client_cfg["process_substrings"])
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
