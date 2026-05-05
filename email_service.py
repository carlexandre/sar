import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

def enviar_email_com_anexos(destinatario, assunto, corpo, anexos):
    """
    Envia um email com os PDFs gerados.
    anexos deve ser uma lista de tuplas: [("nome_do_arquivo.pdf", bytes_do_pdf)]
    """
    load_dotenv()
    EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
    EMAIL_SENHA = os.getenv("EMAIL_SENHA") # Senha de App (Ex: Google App Passwords)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))

    if not all([EMAIL_REMETENTE, EMAIL_SENHA]):
        print("⚠️ Credenciais de email não configuradas no .env. Email ignorado.")
        return False

    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = destinatario
    msg.set_content(corpo)

    for nome_arquivo, pdf_bytes in anexos:
        msg.add_attachment(
            pdf_bytes, 
            maintype='application', 
            subtype='pdf', 
            filename=nome_arquivo
        )

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_REMETENTE, EMAIL_SENHA)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_REMETENTE, EMAIL_SENHA)
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email para {destinatario}: {e}")
        return False