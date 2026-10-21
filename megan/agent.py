from langchain_litellm import ChatLiteLLM
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_swarm, create_handoff_tool

from common.config import FORMATO_WHATSAPP, MODELO_PRINCIPAL
from weather_time_agent.agent import DESCRIPTION as WEATHER_DESCRIPTION, build_agent as build_weather_agent
from search_agent.agent import DESCRIPTION as SEARCH_DESCRIPTION, build_agent as build_search_agent

MEGAN_STATIC = (
    "Você é a Megan, secretária pessoal. Você é prestativa, educada e "
    "cordial, com tom profissional e acolhedor, como uma boa secretária. "
    "Você mesma responde conversas gerais, dúvidas de conhecimento geral, "
    "ajuda com textos e ideias. "
    "Para pedidos que um especialista atende, transfira para ele, "
    "conforme a descrição de cada um:\n"
    f"- weather_time_agent: {WEATHER_DESCRIPTION}\n"
    f"- search_agent: {SEARCH_DESCRIPTION}\n"
    "Se ninguém atender um pedido que exige dados reais (como e-mails), "
    "diga com educação que ainda não tem acesso a isso, sem inventar. "
    + FORMATO_WHATSAPP
    + "Responda sempre em português (pt-BR)."
)

def build_megan_agent():
    handoff_to_weather = create_handoff_tool(
        agent_name="weather_time_agent",
        description="Transfere a conversa para o especialista em clima e horário.",
    )
    handoff_to_search = create_handoff_tool(
        agent_name="search_agent",
        description="Transfere a conversa para o especialista em pesquisas na internet",
    )
    return create_react_agent(
        model=ChatLiteLLM(model=MODELO_PRINCIPAL),
        tools=[handoff_to_weather, handoff_to_search],
        prompt=MEGAN_STATIC,
        name="megan",
    )

def build_workflow():
    megan_agent = build_megan_agent()
    weather_agent = build_weather_agent()
    search_agent = build_search_agent()
    return create_swarm(
        agents=[megan_agent, weather_agent, search_agent],
        default_active_agent="megan",
    )

app = build_workflow().compile()