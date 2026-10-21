import os
import datetime
from zoneinfo import ZoneInfo

MODELO_PRINCIPAL = os.getenv("MODELO_PRINCIPAL", "gemini/gemini-3.8-flash")
MODELO_RESERVA = os.getenv("MODELO_RESERVA", "groq/qwen/qwen3.8-27b")

FORMATO_WHATSAPP = (
    "Suas respostas são lidas no WhatsApp: use *texto* para negrito, "
    "listas com - texto são permitidas, "
    "não use tabelas nem títulos com #, e seja breve. "
)

DIAS_SEMANA = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo",
]

def agora_brasilia() -> datetime.datetime:
    return datetime.datetime.now(ZoneInfo("America/Sao_Paulo"))

def data_hora_extenso() -> str:
    agora = agora_brasilia()
    return (
        f"{DIAS_SEMANA[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}, "
        f"{agora.strftime('%H:%M')}"
    )