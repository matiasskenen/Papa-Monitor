from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any

import resend
from flask import Flask, jsonify, request
from supabase import Client, create_client
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- Solo variables de entorno (sin secretos en el código) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip() # Idealmente Service Role Key para el backend
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "").strip()

supabase: Client | None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Destino fijo de alertas (por ahora siempre este correo)
ALERT_EMAIL_TO = "matias.skenen@gmail.com"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_supabase():
    if supabase is None:
        return jsonify({"error": "Servidor sin SUPABASE configurado"}), 503
    return None


def _cfg_get(key: str, default: Any = None) -> Any:
    if supabase is None:
        return default
    try:
        r = supabase.table("config").select("value").eq("key", key).limit(1).execute()
        rows = r.data or []
        if not rows:
            return default
        return rows[0].get("value", default)
    except Exception:
        return default


def _cfg_set(key: str, value: Any) -> None:
    if supabase is None:
        raise RuntimeError("supabase")
    val = value
    if isinstance(val, bool):
        val = "true" if val else "false"
    elif val is not None and not isinstance(val, str):
        val = str(val)
    # Usamos upsert para no fallar si la row no existe
    existing = supabase.table("config").select("key").eq("key", key).limit(1).execute().data or []
    if existing:
        supabase.table("config").update({"value": val}).eq("key", key).execute()
    else:
        supabase.table("config").insert({"key": key, "value": val}).execute()


def _cfg_upsert(key: str, value: Any) -> None:
    if supabase is None:
        raise RuntimeError("supabase")
    val = value
    if isinstance(val, bool):
        val = "true" if val else "false"
    elif val is not None and not isinstance(val, str):
        val = str(val)
    existing = supabase.table("config").select("key").eq("key", key).limit(1).execute().data or []
    if existing:
        supabase.table("config").update({"value": val}).eq("key", key).execute()
    else:
        supabase.table("config").insert({"key": key, "value": val}).execute()


def emails_enabled() -> bool:
    v = _cfg_get("emails_enabled", "true")
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "1", "yes", "on")


def alert_email() -> str:
    return str(_cfg_get("alert_email") or os.environ.get("ALERT_EMAIL", "") or "").strip()


def resend_from_address() -> str:
    return str(_cfg_get("resend_from") or os.environ.get("RESEND_FROM", "") or "onboarding@resend.dev").strip()


def admin_auth(f):
    """Sin autenticación — acceso público."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        s = str(val).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _session_minutes_by_calendar_day(start_utc: datetime, end_utc: datetime, tz: ZoneInfo) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    if end_utc <= start_utc:
        return dict(out)
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    d = start_local.date()
    end_date = end_local.date()
    while d <= end_date:
        day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        seg_start = max(start_local, day_start)
        seg_end = min(end_local, day_end)
        if seg_end > seg_start:
            out[d.isoformat()] += (seg_end - seg_start).total_seconds() / 60.0
        d = d + timedelta(days=1)
    return dict(out)


@app.route("/api/public-config", methods=["GET"])
def public_config():
    err = require_supabase()
    if err:
        return err
    try:
        raw_proc = _cfg_get("process_substrings")
        if isinstance(raw_proc, str) and raw_proc.strip().startswith("["):
            try:
                proc_list = json.loads(raw_proc)
            except json.JSONDecodeError:
                proc_list = [x.strip() for x in raw_proc.split(",") if x.strip()]
        elif isinstance(raw_proc, list):
            proc_list = raw_proc
        else:
            proc_list = [
                "FortniteClient-Win64-Shipping",
                "FortniteClient-Win64-Shipping_BE",
            ]
        poll = _cfg_get("poll_interval_seconds", "20")
        try:
            poll_i = int(poll)
        except (TypeError, ValueError):
            poll_i = 20
        poll_i = max(10, min(poll_i, 300))
        base = os.environ.get("PUBLIC_API_BASE", "").strip().rstrip("/")
        if not base and request.host_url:
            base = request.host_url.rstrip("/")
        return jsonify(
            {
                "api_base": base or None,
                "process_substrings": proc_list,
                "poll_interval_seconds": poll_i,
                "supabase_url": SUPABASE_URL,
                "supabase_anon_key": SUPABASE_ANON_KEY
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/heal-profile", methods=["POST"])
def heal_profile():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "No auth token provided"}), 401
    jwt_token = auth_header.split(" ")[1]

    try:
        user_res = supabase.auth.get_user(jwt_token)
        if not user_res or not user_res.user:
            return jsonify({"error": "Invalid auth token"}), 401
        user_id = user_res.user.id
        email = user_res.user.email
    except Exception as e:
        return jsonify({"error": f"Auth error: {str(e)}"}), 401
    
    try:
        from random import randint
        # Verificar si existe el perfil usando admin role
        profile = sb_admin.table("users_profiles").select("id").eq("id", user_id).execute()
        if not profile.data:
            # Insertar uno nuevo manualmente
            new_code = str(randint(100000, 999999))
            sb_admin.table("users_profiles").insert({
                "id": user_id,
                "email": email or f"fantasma_{user_id}@app.com",
                "display_name": email.split('@')[0] if email else "Usuario",
                "friend_code": new_code
            }).execute()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error curando perfil fantasma: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET", "POST"])
def handle_status():
    err = require_supabase()
    if err:
        return err

    # Validación de token JWT (para POST y GET)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "No auth token provided"}), 401
    jwt_token = auth_header.split(" ")[1]

    try:
        user_res = supabase.auth.get_user(jwt_token)
        if not user_res or not user_res.user:
            return jsonify({"error": "Invalid auth token"}), 401
        user_id = user_res.user.id
    except Exception as e:
        return jsonify({"error": f"Auth error: {str(e)}"}), 401

    if request.method == "GET":
        try:
            try:
                supabase.rpc("cerrar_sesiones_muertas").execute()
            except Exception:
                pass
            try:
                limit = int(request.args.get("limit", "10"))
            except (TypeError, ValueError):
                limit = 10
            limit = max(1, min(limit, 50))
            # OJO: La db tiene RLS, pero el backend aqui usa la Service Role (probablemente).
            # Por seguridad en `/api/status` GET deberíamos filtrar por él mismo y sus amigos, 
            # pero lo ideal es que el JS llame a supabase.from("sessions") directamente con su token.
            # Mantenemos este endpoint con filtro simple por user_id por compatibilidad si es llamado localmente
            res = supabase.table("sessions").select("*").eq("user_id", user_id).order("start_time", desc=True).limit(limit).execute()
            return jsonify(res.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        try:
            data = request.json or {}
            is_online = bool(data.get("is_online", False))
            
            # Buscar sesión activa para este usuario en particular
            active_res = supabase.table("sessions").select("*").eq("user_id", user_id).eq("is_active", True).execute()
            active_session = active_res.data or []
            now = utc_now_iso()

            if is_online:
                if not active_session:
                    supabase.table("sessions").insert(
                        {
                            "user_id": user_id,
                            "is_active": True,
                            "last_heartbeat": now,
                            "start_time": now,
                        }
                    ).execute()
                    
                    if RESEND_API_KEY:
                        # Buscar a todos los perfiles que tienen a este usuario fijado
                        subs_res = supabase.table("users_profiles").select("email").eq("pinned_friend_id", user_id).execute()
                        subscribers = [r["email"] for r in (subs_res.data or []) if r.get("email")]
                        
                        # Buscar nombre display del usuario
                        prof_res = supabase.table("users_profiles").select("display_name").eq("id", user_id).execute()
                        dname = prof_res.data[0]["display_name"] if prof_res.data else "Un amigo"

                        for emp in subscribers:
                            try:
                                resend.Emails.send(
                                    {
                                        "from": resend_from_address(),
                                        "to": emp,
                                        "subject": f"⚠️ {dname} se ha conectado a Fortnite",
                                        "html": f"<strong>{dname} acaba de abrir el juego y está ONLINE.</strong><br><br>Este email fue enviado automáticamente por PapaMonitor, dado que lo tienes como amigo fijado.",
                                    }
                                )
                            except Exception as e:
                                print(f"Error Resend to {emp}: {e}")

                else:
                    supabase.table("sessions").update({"last_heartbeat": now}).eq("id", active_session[0]["id"]).execute()
            elif active_session:
                supabase.table("sessions").update({"is_active": False, "end_time": now}).eq("id", active_session[0]["id"]).execute()

            return jsonify({"status": "ok"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/config", methods=["GET", "POST"])
def handle_config():
    err = require_supabase()
    if err:
        return err
    try:
        if request.method == "GET":
            rows = supabase.table("config").select("*").eq("key", "emails_enabled").limit(1).execute().data or []
            if not rows:
                return jsonify({"key": "emails_enabled", "value": "true"}), 200
            return jsonify(rows[0]), 200
        if request.method == "POST":
            body = request.json or {}
            if "enabled" not in body:
                return jsonify({"error": "enabled requerido"}), 400
            str_val = "true" if body.get("enabled") else "false"
            supabase.table("config").update({"value": str_val}).eq("key", "emails_enabled").execute()
            return jsonify({"status": "updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/stats/playtime", methods=["GET"])
def playtime_stats():
    err = require_supabase()
    if err:
        return err
    try:
        days = int(request.args.get("days", "30"))
    except (TypeError, ValueError):
        days = 30
    days = max(1, min(days, 90))
    tz_name = request.args.get("tz", "Europe/Madrid")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Madrid")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        res = (
            supabase.table("sessions")
            .select("*")
            .gte("start_time", cutoff.isoformat())
            .order("start_time", desc=False)
            .limit(500)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    by_day: dict[str, float] = defaultdict(float)
    for row in rows:
        start = _parse_dt(row.get("start_time"))
        if not start:
            continue
        if row.get("is_active"):
            end = datetime.now(timezone.utc)
        else:
            end = _parse_dt(row.get("end_time")) or datetime.now(timezone.utc)
        for d, mins in _session_minutes_by_calendar_day(start, end, tz).items():
            by_day[d] += mins

    series = sorted(({"date": k, "minutes": round(v, 1)} for k, v in by_day.items()), key=lambda x: x["date"])
    return jsonify({"timezone": tz_name, "days": days, "by_day": series}), 200


@app.route("/api/admin/settings", methods=["GET", "POST"])
@admin_auth
def admin_settings():
    err = require_supabase()
    if err:
        return err
    keys = (
        "emails_enabled",
        "alert_email",
        "resend_from",
        "process_substrings",
        "poll_interval_seconds",
    )
    if request.method == "GET":
        out = {}
        for k in keys:
            v = _cfg_get(k)
            if k == "process_substrings" and isinstance(v, str) and v.strip().startswith("["):
                try:
                    out[k] = json.loads(v)
                except json.JSONDecodeError:
                    out[k] = v
            else:
                out[k] = v
        return jsonify(out), 200
    body = request.json or {}
    try:
        for k in keys:
            if k not in body:
                continue
            v = body[k]
            if k == "process_substrings" and isinstance(v, list):
                _cfg_upsert(k, json.dumps(v))
            elif k == "emails_enabled":
                _cfg_upsert(k, "true" if v else "false")
            else:
                _cfg_upsert(k, v)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test-email", methods=["POST"])
@admin_auth
def test_email():
    """Envía un email de prueba para verificar que Resend funciona."""
    if not RESEND_API_KEY:
        return jsonify({"error": "RESEND_API_KEY no configurada en el servidor"}), 503
    try:
        resend.Emails.send(
            {
                "from": resend_from_address(),
                "to": ALERT_EMAIL_TO,
                "subject": "✅ PapaMonitor — Test de email OK",
                "html": "<strong>El sistema de emails está funcionando correctamente.</strong><br><br>Este es un email de prueba enviado desde el panel de administración.",
            }
        )
        return jsonify({"status": "ok", "message": f"Email enviado a {ALERT_EMAIL_TO}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500





if __name__ == "__main__":
    app.run(debug=True, port=5000)
