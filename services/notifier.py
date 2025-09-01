# notifier.py
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import logging
from pathlib import Path

logger = logging.getLogger("Notifier")

def send_google_chat_alert(webhook_url: str, message: str):
    """
    Envia uma mensagem de alerta para o Google Chat via Webhook.

    :param webhook_url: URL do webhook do Google Chat
    :param message: Mensagem a ser enviada
    """
    try:
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        payload = {"text": message}

        response = requests.post(webhook_url, headers=headers, json=payload)
        response.raise_for_status()

        logger.info("🔔 Alerta enviado para Google Chat com sucesso!")

    except Exception as e:
        logger.error(f"Erro ao enviar alerta para Google Chat: {e}")
        raise


# from notifier import send_google_chat_alert

# send_google_chat_alert(
#     webhook_url="https://chat.googleapis.com/v1/spaces/.../messages?key=...",
#     message="🚨 Novo scan foi executado!"
# )
