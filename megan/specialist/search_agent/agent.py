
from langgraph.prebuilt import create_react_agent
from langchain_litellm import ChatLiteLLM
from langgraph_swarm import create_handoff_tool

from common.config import FORMATO_WHATSAPP, MODELO_PRINCIPAL
from ddgs import DDGS
from ddgs.exceptions import DDGSException

MAX_RESULTADOS = 5

def buscar_na_internet(query: str) -> dict:
    """Pesquisa um termo na internet e devolve os resultados mais relevantes
    Use para perguntas sobre fatos atuais, notícias, preços ou qualquer
    informação que não esteja no seu conhecimento ou que possa ter mudado
    recentemente.
    Args:
        query: O que pesquisar (ex: "cotação do dólar hoje").
    Returns:
        dict com "status" ("success" ou "error") e, em caso de sucesso,
        "resultados": lista com "título", "link" e "resumo" de cada página
        encontrada. Em caso de erro, "error_message".
    """

    try:
        resultados = DDGS().text(query, max_results=MAX_RESULTADOS)
    except DDGSException  as e:
        return {"status": "error", "error_message": f"Falha ao pesquisar: {e}"}
    if not resultados:
        return {"status": "error", "error_message": f"Nenhum resultado encontrado."}
    return {
        "status": "success",
        "resultados": [
            {"titulo": r.get("title", ""), "link": r.get("href", ""), "resumo": r.get("body", "")}
            for r in resultados
        ],
    }

DESCRIPTION = (
    "Especialista em pesquisas na internet: busca fatos atuais, notícias, "
    "preços e qulquer informação que exija dados recentes da web."
)

def build_agent():
    handoff_to_megan = create_handoff_tool(
        agent_name="megan",
        description="Transferir a conversa de volta para a Megan quando o pedido não for sobre pesquisa na internet"
    )
    return create_react_agent(
        model=ChatLiteLLM(model=MODELO_PRINCIPAL),
        tools=[buscar_na_internet, handoff_to_megan],
        prompt=(
            "Você é um especialista em pesquisas na internet. "
            "Antes de fazer qualquer coisa, confira se o pedido exige uma "
            "busca na web. Se NÃO exigir, não tente responder e não use "
            "buscar_na_internet — chame imediatamente a ferramenta de "
            "transferência para a megan, sem fazer mais nada. "
            "Use buscar_na_internet para pesquisar o que o usuário pediu. "
            "Baseie sua resposta apenas nos resultados encontrados, nunca "
            "invente informações que não vieram da busca. Cite a fonte "
            "(o link) quando relevante. Se não encontrar nada relevante, "
            "diga isso ao usuário. "
            + FORMATO_WHATSAPP
            + "Responda sempre em português (pt-BR)."
        ),
        name="search_agent",
    )

root_agent = build_agent()