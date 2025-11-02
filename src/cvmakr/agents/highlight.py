"""Secondary agent to apply LaTeX emphasis to generated bullets."""

from __future__ import annotations

import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class _HighlightResponse(BaseModel):
    bullet_points: str


def wrapper_agent(internship: str, job_description: str) -> str:
    """Add ``\\textbf`` emphasis markers without modifying existing bullet text."""

    parser = PydanticOutputParser(pydantic_object=_HighlightResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''
You are a professional ATS resume expert. Your inputs are:
    1. A text file containing one of my project or internship experiences described exhaustively (or my summary).
    2. A job description for the role I�?Tm applying to.

INSTRUCTIONS:
            - Read the bullet points as they are and do not change their content or structure. Your task is only to identify important technical or impactful words (such as tools, actions, or results) and wrap at least one per bullet point using the LaTeX \\textbf command for emphasis.
            - Do not reword or reformat anything else.
             
             
<PROJECT/INTERNSHIP>
{internship}
</COURSE/SKILL LIST>
             
<JOB DESCRIPTION>
{job_description}
</JOB DESCRIPTION>
         
---

Now, please process that input and output your five ATS-optimized picks.
        
---
CRUCIAL: The output should be in french. (its a french resume)
---             

OUTPUT
Return one JSON object for this schema and nothing else:
{format_instructions}
''',
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])

    executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = executor.invoke(
        {
            "job_description": job_description,
            "agent_scratchpad": "",
            "internship": internship,
        }
    )
    data = json.loads(raw_response["output"])
    return data["bullet_points"]

