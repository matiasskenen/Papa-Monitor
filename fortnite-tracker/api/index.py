from flask import Flask, request, jsonify
import os
from supabase import create_client
from resend import Emails

app = Flask(__name__)

# Inicialización con manejo de errores
try:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)
    RESEND_API_KEY = os.environ.get("RESEND_KEY")
except Exception as e:
    print(f"Error inicializando clientes: {e}")

@app.route('/api/status', methods=['POST'])
def handle_status():
    try:
        data = request.json
        is_online = data.get("is_online", False)
        
        # 1. Intentar leer de Supabase
        res = supabase.table("sessions").select("*").eq("is_active", True).execute()
        active_session = res.data
        
        if is_online and not active_session:
            # 2. Intentar Insertar
            supabase.table("sessions").insert({"is_active": True}).execute()
            
            # 3. Intentar mandar Mail (si falla el mail, que no rompa el resto)
            try:
                if RESEND_API_KEY:
                    Emails.send({
                        "from": "FortniteTracker <onboarding@resend.dev>",
                        "to": ["tu-email@gmail.com"], # <--- CAMBIÁ ESTO
                        "subject": "⚠️ PAPÁ ONLINE",
                        "html": "<strong>Se conectó al Fortnite.</strong>"
                    }, api_key=RESEND_API_KEY)
            except Exception as mail_err:
                print(f"Error enviando mail: {mail_err}")
                
        elif not is_online and active_session:
            # 4. Intentar Cerrar Sesión
            session_id = active_session[0]['id']
            supabase.table("sessions").update({
                "is_active": False, 
                "end_time": "now()"
            }).eq("id", session_id).execute()
            
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        # Esto va a imprimir el error real en los Logs de Vercel
        print(f"ERROR DETECTADO: {str(e)}")
        return jsonify({"error": str(e)}), 500