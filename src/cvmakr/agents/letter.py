"""Agent that drafts the motivation letter."""

from __future__ import annotations

import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SerpAPIWrapper
from pydantic import BaseModel


class _MotivationResponse(BaseModel):
    letter_text: str


def motivation_letter_agent(
    experiences: str, projects: str, background: str, job_description: str
) -> str:
    """
    Generate a concise motivation letter tailored to the supplied job description.
    """

    parser = PydanticOutputParser(pydantic_object=_MotivationResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
    "system",
    """
OBJECTIF  
Rédige une lettre de motivation (en français), ultra-concise et percutante, en respectant la méthode SHARK.

ENTRÉES  
Chaque bloc de texte brut est encadré par des accolades portant son nom :

👉 **experiences**  
{experiences}

👉 **projects**  
{projects}

👉 **background**  
{background}

👉 **job_description**  
{job_description}

RÈGLES  

1. Analyse le ton et l’énergie du **job_description** et reproduis-les dès la première phrase et tout au long de la lettre (ex : dynamique, ambitieux, innovant).

2. Priorise mes compétences actuelles et ma motivation forte, sans te limiter à décrire tes expériences passées. Utilise-les pour illustrer ta capacité à relever les défis du poste (seulement si elles sont pertinentes).

3. Effectue une recherche rapide sur l’entreprise (site officiel, actualités) pour identifier une valeur clé ou un fait récent. Intègre cet élément pour montrer ta compréhension et ton alignement avec leur culture.

4. Structure la lettre selon SHARK en 12 à 15 phrases :

   - **Situation** : qui tu es + pourquoi ce poste, avec le ton du job description.  
   - **Hindrance** : défi principal du poste.  
   - **Action + Résultat** : 1 phrase par compétence, illustrée par tes capacités actuelles.  
   - **Kick-off** : phrase de clôture énergique, montrant ta détermination féroce à convaincre en entretien.

5. Longueur totale : ≤ 1000 caractères (espaces compris).

6. Ton : professionnel, énergique, déterminé, humble, en miroir avec l’énergie du job description.

7. Aucune salutation initiale, aucune formule de politesse finale, aucune signature.

8- Soit humain et authentique, évite le langage trop formel ou robotique.

SORTIE  
Retourne **exactement** cet objet JSON (aucun texte en dehors) :

RETURN exactement un objet JSON selon ce schéma (et rien d'autre) :  
{format_instructions}
""",
        ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    serp = SerpAPIWrapper()
    web_search_tool = Tool(
        name="web_search",
        func=serp.run,
        description="Utilisez pour rechercher des informations sur l'entreprise cible lorsque nǸcessaire via SerpAPI.",
    )
    tools = [web_search_tool]

    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    with open(experiences, "r", encoding="utf-8") as file:
        experiences_content = file.read()
    with open(projects, "r", encoding="utf-8") as file:
        projects_content = file.read()
    with open(background, "r", encoding="utf-8") as file:
        background_content = file.read()

    raw = executor.invoke(
        {
            "experiences": experiences_content,
            "projects": projects_content,
            "background": background_content,
            "job_description": job_description,
            "agent_scratchpad": "",
        }
    )
    output = json.loads(raw["output"])
    return output["letter_text"]

