from flask import Flask, request, jsonify
import os
from supabase import create_client
from resend import Emails

app = Flask(__name__)

# Configuración de clientes con variables de entorno
try:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)
    RESEND_API_KEY = os.environ.get("RESEND_KEY")
except Exception as e:
    print(f"Error inicializando: {e}")

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    # --- MÉTODO GET: Para que la página web vea los datos ---
    if request.method == 'GET':
        try:
            # Traemos las últimas 10 sesiones ordenadas por la más reciente
            res = supabase.table("sessions").select("*").order("start_time", desc=True).limit(10).execute()
            return jsonify(res.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- MÉTODO POST: Para que el monitor mande el Online/Offline ---
    try:
        data = request.json
        is_online = data.get("is_online", False)
        
        # Buscamos si hay alguna sesión marcada como activa
        res = supabase.table("sessions").select("*").eq("is_active", True).execute()
        active_session = res.data
        
        if is_online and not active_session:
            # INICIO DE SESIÓN
            supabase.table("sessions").insert({"is_active": True}).execute()
            
            # Envío de mail opcional (Resend)
            try:
                if RESEND_API_KEY:
                    Emails.send({
                        "from": "FortniteTracker <onboarding@resend.dev>",
                        "to": ["tu-mail@gmail.com"], # <--- PONÉ TU MAIL REAL ACÁ
                        "subject": "⚠️ PAPÁ SE CONECTÓ",
                        "html": "<strong>El viejo acaba de abrir el Fortnite.</strong>"
                    }, api_key=RESEND_API_KEY)
            except:
                pass
                
        elif not is_online and active_session:
            # CIERRE DE SESIÓN
            session_id = active_session[0]['id']
            supabase.table("sessions").update({
                "is_active": False, 
                "end_time": "now()"
            }).eq("id", session_id).execute()
            
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error en POST: {str(e)}")
        return jsonify({"error": str(e)}), 500