import datetime
import httpx
from zoneinfo import ZoneInfo
from langgraph.prebuilt import create_react_agent
from langchain_litellm import ChatLiteLLM
from langgraph_swarm import create_handoff_tool
from common.config import DIAS_SEMANA, FORMATO_WHATSAPP, MODELO_PRINCIPAL

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10

WMO_CODES = {
    0: "céu limpo",
    1: "predominantemente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "neblina",
    48: "neblina com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa intensa",
    56: "garoa congelante fraca",
    57: "garoa congelante intensa",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "grãos de neve",
    80: "pancadas de chuva fracas",
    81: "pancadas de chuva moderadas",
    82: "pancadas de chuva violentas",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoada",
    96: "trovoada com granizo fraco",
    99: "trovoada com granizo forte"
}

def _geocode(city: str) -> dict | None:
    resp = httpx.get(
        GEOCODING_URL,
        params={"name": city, "count": 1, "language": "pt", "format": "json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json().get("results")

    if not results:
        return None

    place = results[0]
    return {
        "name": place["name"],
        "region": place.get("admin1", ""),
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone", "UTC"),
    }

def get_weather(city: str) -> dict:
    """Retorna o clima ATUAL (neste momento) de uma cidade.
    Use para perguntas como "como está o tempo agora em X?" ou
    "está chovendo em X?". Para dias futuros, use get_forecast ou
    get_hourly_forecast.
    Args:
        city: Nome da cidade, sem estado ou país (ex.: "Araraquara").
    Returns:
        dict com "status" ("success" ou "error") e, em caso de sucesso,
        "report" com condição, temperatura, sensação térmica, umidade e
        vento. Em caso de erro, "error_message" com o motivo.
    """
    try:
        place = _geocode(city)
        if place is None:
            return {
                "status": "error",
                "error_message": f"Não encontrei a cidade '{city}'.",
            }

        resp = httpx.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,"
                           "relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        current = resp.json()["current"]

    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_message": f"Falha ao consultar o serviço de clima: {e}",
        }

    condition = WMO_CODES.get(current["weather_code"], "condição desconhecida")
    location = ", ".join(p for p in (place["name"], place["region"], place["country"]) if p)

    report = (
        f"Clima atual em {location}: {condition}, "
        f"{current['temperature_2m']} °C "
        f"(sensação de {current['apparent_temperature']} °C), "
        f"umidade de {current['relative_humidity_2m']}%, "
        f"vento de {current['wind_speed_10m']} km/h."
    )
    return {"status": "success", "report": report}

def get_current_time(city: str) -> dict:
    """Retorna a data e a hora ATUAIS (relógio) no fuso horário de uma cidade.
    Use para perguntas como "que horas são em X?". Não serve para
    previsão do tempo por hora; para isso, use get_hourly_forecast.
    Args:
        city: Nome da cidade, sem estado ou país (ex.: "Tóquio").
    Returns:
        dict com "status" ("success" ou "error") e, em caso de sucesso,
        "report" com hora, data e fuso. Em caso de erro, "error_message".
    """
    try:
        place = _geocode(city)
    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_message": f"Falha ao consultar o serviço de geocodificação: {e}",
        }

    if place is None:
        return {
            "status": "error",
            "error_message": f"Não encontrei a cidade '{city}'.",
        }

    now = datetime.datetime.now(ZoneInfo(place["timezone"]))
    report = (
        f"Agora em {place['name']} são {now.strftime('%H:%M')} "
        f"do dia {now.strftime('%d/%m/%Y')} (fuso {place['timezone']})."
    )
    return {"status": "success", "report": report}

def get_forecast(city: str, days: int) -> dict:
    """Retorna a previsão do tempo DIÁRIA de uma cidade, começando por hoje.
    Use para perguntas sobre os próximos dias, a semana ou o fim de
    semana. Escolha "days" de modo a cobrir o último dia pedido e depois
    filtre pelo campo "dia_semana" (ex.: para o fim de semana, peça 7
    dias e use sábado e domingo).
    Args:
        city: Nome da cidade, sem estado ou país (ex.: "Araraquara").
        days: Quantidade de dias a partir de hoje (1 = só hoje), de 1 a 16.
    Returns:
        dict com "status", "cidade" e "previsao": lista de dias, cada um
        com data, dia_semana, condicao, temp_max, temp_min,
        chance_de_chuva_pct e chuva_mm. Em caso de erro, "error_message".
    """
    days = max(1, min(days, 16))

    try:
        place = _geocode(city)
        if place is None:
            return {
                "status": "error",
                "error_message": f"Não encontrei a cidade '{city}'.",
            }
        resp = httpx.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,precipitation_sum",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        daily = resp.json()["daily"]

    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_message": f"Falha ao consultar previsão do tempo: {e}",
        }

    forecast = []
    for date_str, code, t_max, t_min, rain_prob, rain_mm in zip(
        daily["time"],
        daily["weather_code"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_probability_max"],
        daily["precipitation_sum"],
    ):
        date = datetime.datetime.fromisoformat(date_str)
        forecast.append({
            "data": date.strftime("%d/%m/%Y"),
            "dia_semana": DIAS_SEMANA[date.weekday()],
            "condicao": WMO_CODES.get(code, "condição desconhecida"),
            "temp_max": t_max,
            "temp_min": t_min,
            "chance_de_chuva_pct": rain_prob,
            "chuva_mm": rain_mm,
        })

    location = ", ".join(p for p in (place["name"], place["region"], place["country"]) if p)
    return {"status": "success", "cidade": location, "previsao": forecast}

def get_hourly_forecast(city: str, day_offset: int) -> dict:
    """Retorna a previsão do tempo HORA A HORA (24 horas) de um único dia.
    Use para perguntas como "vai chover amanhã à tarde em X?" ou
    "qual a previsão por hora para hoje?". O dia é relativo a hoje no
    fuso da cidade; a data exata é calculada pela ferramenta.
    Args:
        city: Nome da cidade, sem estado ou país (ex.: "Araraquara").
        day_offset: Dias a partir de hoje: 0 = hoje, 1 = amanhã,
            2 = depois de amanhã, até 15.
    Returns:
        dict com "status", "cidade", "data", "dia_semana" e
        "previsao_horaria": lista de horas, cada uma com hora, condicao,
        temp, chance_de_chuva_pct, chuva_mm e vento_kmh.
        Em caso de erro, "error_message".
    """
    day_offset = max(0, min(day_offset, 15))

    try:
        place = _geocode(city)
        if place is None:
            return {
                "status": "error",
                "error_message": f"Não encontrei a cidade: '{city}'.",
            }
        today = datetime.datetime.now(ZoneInfo(place["timezone"])).date()
        target = today + datetime.timedelta(days=day_offset)

        resp = httpx.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "hourly": "temperature_2m,precipitation_probability,"
                          "precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
                "start_date": target.isoformat(),
                "end_date": target.isoformat(),
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        hourly = resp.json()["hourly"]

    except httpx.HTTPError as e:
        return {
            "status": "error",
            "error_message": f"Falha ao consultar previsão horária: {e}",
        }

    hours = []
    for time_str, temp, rain_prob, rain_mm, code, wind in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        hourly["precipitation"],
        hourly["weather_code"],
        hourly["wind_speed_10m"],
    ):
        dt = datetime.datetime.fromisoformat(time_str)
        hours.append({
            "hora": dt.strftime("%H:%M"),
            "condicao": WMO_CODES.get(code, "condição desconhecida"),
            "temp": temp,
            "chance_de_chuva_pct": rain_prob,
            "chuva_mm": rain_mm,
            "vento_kmh": wind,
        })

    return {
        "status": "success",
        "cidade": place["name"],
        "data": target.strftime("%d/%m/%Y"),
        "dia_semana": DIAS_SEMANA[target.weekday()],
        "previsao_horaria": hours,
    }

DESCRIPTION = (
    "Especialista em clima e horário: clima atual, previsão do tempo "
    "diária e hora a hora (até 16 dias) e hora local de qualquer cidade."
)

def build_agent():
    handoff_to_megan = create_handoff_tool(
        agent_name="megan",
        description="Transfere a conversa de volta para a Megan quando o pedido não for sobre clima ou horário.",
    )
    return create_react_agent(
        model=ChatLiteLLM(model=MODELO_PRINCIPAL),
        tools=[get_weather, get_current_time, get_forecast, get_hourly_forecast, handoff_to_megan],
        prompt=(
            "Você é um especialista que informa o clima e a hora atuais de cidades. "
            "Antes de fazer qualquer coisa, confira se o pedido é sobre clima, "
            "previsão do tempo ou horário. Se NÃO for, não tente responder e não "
            "use get_weather, get_current_time, get_forecast nem "
            "get_hourly_forecast — chame imediatamente a ferramenta de "
            "transferência para a megan, sem fazer mais nada. "
            "Se for sobre clima/horário, use a ferramenta get_weather para "
            "perguntas sobre clima e get_current_time para perguntas sobre "
            "horário. "
            "Use get_forecast e get_hourly_forecast para perguntas sobre os "
            "próximos dias e horário, respectivamente. "
            "Ao apresentar a previsão horária, resuma por períodos (madrugada, "
            "manhã, tarde, noite). "
            "Destaque horários com chuva, a menos que o usuário peça todas as "
            "horas. "
            "Ao chamar as ferramentas, passe apenas o nome da cidade. "
            "Se uma ferramenta retornar erro, explique o problema ao usuário. "
            + FORMATO_WHATSAPP
            + "Responda sempre em português (pt-BR)."
        ),
        name="weather_time_agent",
    )

root_agent = build_agent()