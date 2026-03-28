from flask import Flask, request, jsonify
import os
from supabase import create_client
from resend import Emails

app = Flask(__name__)

# Configuración (Asegurate que estén en Vercel Settings)
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
RESEND_API_KEY = os.environ.get("RESEND_KEY")

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    if request.method == 'GET':
        try:
            # Limpia sesiones viejas antes de mostrar los datos
            supabase.rpc('cerrar_sesiones_muertas').execute()
            res = supabase.table("sessions").select("*").order("start_time", desc=True).limit(10).execute()
            return jsonify(res.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.json
            is_online = data.get("is_online", False)
            
            # Verificamos si los mails están prendidos en la DB
            conf = supabase.table("config").select("value").eq("key", "emails_enabled").single().execute()
            emails_allowed = conf.data.get("value", True)

            # Verificamos si hay sesión activa
            active_res = supabase.table("sessions").select("*").eq("is_active", True).execute()
            active_session = active_res.data

            if is_online:
                if not active_session:
                    # NUEVA SESIÓN
                    supabase.table("sessions").insert({"is_active": True, "last_heartbeat": "now()"}).execute()
                    if emails_allowed and RESEND_API_KEY:
                        Emails.send({
                            "from": "FortniteTracker <onboarding@resend.dev>",
                            "to": ["tu-mail@gmail.com"], # <--- PONÉ TU MAIL
                            "subject": "⚠️ PAPÁ ONLINE",
                            "html": "<strong>El viejo entró al Fortnite ahora.</strong>"
                        }, api_key=RESEND_API_KEY)
                else:
                    # ACTUALIZAR LATIDO (Heartbeat)
                    supabase.table("sessions").update({"last_heartbeat": "now()"}).eq("id", active_session[0]['id']).execute()
            
            elif not is_online and active_session:
                # CIERRE NORMAL
                supabase.table("sessions").update({"is_active": False, "end_time": "now()"}).eq("id", active_session[0]['id']).execute()
                
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'GET':
        res = supabase.table("config").select("*").eq("key", "emails_enabled").single().execute()
        return jsonify(res.data)
    if request.method == 'POST':
        val = request.json.get("enabled")
        supabase.table("config").update({"value": val}).eq("key", "emails_enabled").execute()
        return jsonify({"status": "updated"})