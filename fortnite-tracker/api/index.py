from flask import Flask, request, jsonify
import os
from supabase import create_client
from resend import Emails

app = Flask(__name__)

# Credenciales de entorno en Vercel
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
RESEND_API_KEY = os.getenv("RESEND_KEY")

@app.route('/api/status', methods=['POST'])
def handle_status():
    data = request.json
    is_online = data.get("is_online")
    
    # Buscar si hay una sesión abierta actualmente
    query = supabase.table("sessions").select("*").eq("is_active", True).execute()
    active_session = query.data
    
    # CASO 1: Se conectó (Online y no hay sesión activa)
    if is_online and not active_session:
        supabase.table("sessions").insert({"is_active": True}).execute()
        # Enviar mail con Resend
        if RESEND_API_KEY:
            params = {
                "from": "FortniteTracker <onboarding@resend.dev>",
                "to": ["tu-email@gmail.com"],
                "subject": "⚠️ ALERTA: Papá entró a jugar",
                "html": "<strong>El viejo se conectó al Fortnite recién.</strong>"
            }
            Emails.send(params, api_key=RESEND_API_KEY)
            
    # CASO 2: Se desconectó (Offline y había sesión activa)
    elif not is_online and active_session:
        session_id = active_session[0]['id']
        supabase.table("sessions").update({
            "is_active": False, 
            "end_time": "now()"
        }).eq("id", session_id).execute()
        
    return jsonify({"status": "updated"}), 200