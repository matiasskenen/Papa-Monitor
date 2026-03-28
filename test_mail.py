import resend

resend.api_key = "re_aiajeHT6_24iFMnw5zdM9tYrXwzvzaikv"

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