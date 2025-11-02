"""Agents that prepare internship and professional experience bullet points."""

from __future__ import annotations

import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class _InternshipResponse(BaseModel):
    bullet_points: str


def run_internship_agent(job_description: str, filename: str, number: int) -> str:
    """
    Generate ATS-friendly bullet points for a given internship description.
    """

    parser = PydanticOutputParser(pydantic_object=_InternshipResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''
You are an expert in optimizing resumes for ATS (Applicant Tracking Systems). 

Your task:
- Generate exactly {number} concise, ATS-optimized bullet points in French from the provided internship details, after reading the internship description and the job description and understanding them fully, so you don't make stuff up.

Inputs:
1. Internship description (PROJECT/INTERNSHIP).
2. Job description (JOB DESCRIPTION).

Rules:
- Clearly state tasks and accomplishments respecting the original overall structure.
- Highlight skills and achievements that best match the job description.
- Begin each bullet point with a strong, past-tense action verb (e.g., �� dǸveloppǸ ��).
- Quantify achievements where possible (once or twice max).
- Expand abbreviations at first use (e.g., �� Tonnes mǸtriques (TM) ��).
- Bullet points must represent the essence of the internship, not random matches.
- Maximum one line per bullet point.
- Do not include personal details (name, contact information, etc.).
- Output each bullet point preceded by "-*".
CRUCIAL:
- Keep the original workflow of what i did during the internship. (But you can change the stack and the technologies or even a whole bullet point accordignly to the job description)
- Truthfulness first: 70% of bullet must be anchored in facts from the internship text. You may extend stack details or add a whole bullet only when they are natural complements (e.g., mention Docker to package a service already described as containerised). Flag any inferred tool in your reasoning to stay within a 20% cap.

Here�?Ts your structured input:

<PROJECT/INTERNSHIP>
{internship}
</PROJECT/INTERNSHIP>

<JOB DESCRIPTION>
{job_description}
</JOB DESCRIPTION>

CRUCIAL:
- Return exactly {number} bullet points.
- Output must be in French (verbs in past participle).
- Provide only the bullet points in the following JSON format, nothing else:

{format_instructions}
''',
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions(), number=number)

    llm = ChatOpenAI(model="o3-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])

    with open(filename, "r", encoding="utf-8") as file:
        internship = file.read()

    executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = executor.invoke(
        {
            "job_description": job_description,
            "agent_scratchpad": "",
            "internship": internship,
            "number": number,
        }
    )
    data = json.loads(raw_response["output"])
    bullet_points_str = data["bullet_points"]
    print("used:" + str(number) + " bullet points")
    return bullet_points_str
