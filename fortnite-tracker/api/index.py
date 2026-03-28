from flask import Flask, request, jsonify
from supabase import create_client
import resend
import os

app = Flask(__name__)

# --- CONFIGURACIÓN SEGURA ---
# Intenta leer de Vercel/System, si no usa tus keys reales
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ztcvaoclharvidkaitob.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp0Y3Zhb2NsaGFydmlka2FpdG9iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDY3MTYwMSwiZXhwIjoyMDkwMjQ3NjAxfQ.XQVwWIva46r7w2LOrz4FO4FnCFHmI_lstoYWBP9yo-g")
RESEND_KEY = os.environ.get("RESEND_API_KEY", "re_aiajeHT6_24iFMnw5zdM9tYrXwzvzaikv")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
resend.api_key = RESEND_KEY

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    if request.method == 'GET':
        try:
            # Limpieza opcional de sesiones colgadas
            try: supabase.rpc('cerrar_sesiones_muertas').execute()
            except: pass
            
            res = supabase.table("sessions").select("*").order("start_time", desc=True).limit(10).execute()
            return jsonify(res.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.json
            is_online = data.get("is_online", False)
            
            # 1. Buscar sesión activa
            active_res = supabase.table("sessions").select("*").eq("is_active", True).execute()
            active_session = active_res.data

            if is_online:
                if not active_session:
                    # --- INICIO: INSERT Y MAIL ---
                    supabase.table("sessions").insert({"is_active": True, "last_heartbeat": "now()"}).execute()
                    
                    try:
                        resend.Emails.send({
                            "from": "onboarding@resend.dev",
                            "to": "matias.skenen@gmail.com",
                            "subject": "⚠️ PAPÁ ONLINE",
                            "html": "<strong>El monitor detectó actividad en el proceso.</strong>"
                        })
                    except Exception as e:
                        print(f"Error Resend: {e}")
                else:
                    # --- HEARTBEAT ---
                    supabase.table("sessions").update({"last_heartbeat": "now()"}).eq("id", active_session[0]['id']).execute()
            
            elif not is_online and active_session:
                # --- CIERRE ---
                supabase.table("sessions").update({"is_active": False, "end_time": "now()"}).eq("id", active_session[0]['id']).execute()
            
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    try:
        if request.method == 'GET':
            res = supabase.table("config").select("*").eq("key", "emails_enabled").single().execute()
            return jsonify(res.data)
        if request.method == 'POST':
            val = request.json.get("enabled")
            supabase.table("config").update({"value": val}).eq("key", "emails_enabled").execute()
            return jsonify({"status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)