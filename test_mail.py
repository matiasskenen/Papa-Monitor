import os

import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")
if not resend.api_key:
    raise SystemExit("Definí RESEND_API_KEY en el entorno.")

try:
    r = resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": "matias.skenen@gmail.com", # <--- USÁ ESTE EXÁCTAMENTE
        "subject": "Prueba de Monitor",
        "html": "<strong>¡Ahora sí tiene que llegar!</strong>"
    })
    print("¡Mail enviado con éxito!")
except Exception as e:
    print(f"Error detectado: {e}")