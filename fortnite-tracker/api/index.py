from flask import Flask, request, jsonify
import os
from supabase import create_client
from resend import Emails

app = Flask(__name__)

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
RESEND_API_KEY = os.environ.get("RESEND_KEY")

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    if request.method == 'GET':
        try:
            # Limpieza: Cerramos sesiones colgadas antes de mostrar la data
            supabase.rpc('cerrar_sesiones_muertas').execute()
            res = supabase.table("sessions").select("*").order("start_time", desc=True).limit(10).execute()
            return jsonify(res.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.json
            is_online = data.get("is_online", False)
            res = supabase.table("sessions").select("*").eq("is_active", True).execute()
            active_session = res.data
            
            if is_online:
                if not active_session:
                    # Nueva sesión con latido inicial
                    supabase.table("sessions").insert({"is_active": True, "last_heartbeat": "now()"}).execute()
                    if RESEND_API_KEY:
                        Emails.send({
                            "from": "FortniteTracker <onboarding@resend.dev>",
                            "to": ["tu-mail@gmail.com"],
                            "subject": "⚠️ PAPÁ ONLINE",
                            "html": "<p>El viejo entró al Fortnite.</p>"
                        }, api_key=RESEND_API_KEY)
                else:
                    # Actualizar latido (Heartbeat)
                    session_id = active_session[0]['id']
                    supabase.table("sessions").update({"last_heartbeat": "now()"}).eq("id", session_id).execute()
            
            elif not is_online and active_session:
                # Cierre normal
                session_id = active_session[0]['id']
                supabase.table("sessions").update({"is_active": False, "end_time": "now()"}).eq("id", session_id).execute()
                
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500