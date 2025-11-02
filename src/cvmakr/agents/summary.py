"""Agent for summarising the CV profile."""

from __future__ import annotations

import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class _SummaryResponse(BaseModel):
    bullet_points: str


def run_summary_agent(job_description: str, latex: str) -> str:
    """Generate the CV summary block aligning to the job description."""

    parser = PydanticOutputParser(pydantic_object=_SummaryResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''
### Prompt ###

I am applying for a specific position and would like to craft a compelling CV summary.

### Instructions ###

1. **Job Description:**  
    "{job_description}"

2. **LateX Code of my resume (for context)** 
    "{LateXCode}"            

### Task ###

Using the information provided above, generate a concise and impactful professional summary for my CV.

### Guidelines ###

- **Length:** Limit the summary to 2-4 sentences. (CRUCIAL TO NOT EXCEED THIS LIMIT)  
- **Tone:** Maintain a professional, confident tone.  
- **Content:**  
  - Highlight the most relevant skills and experiences that align with the job description and my passion in backend and AI.  
    
  - Use active language and strong action verbs (e.g., led, developed, implemented).  
  - Avoid generic phrases and clichès; focus on specific strengths and accomplishments.  
  - Don't be too confident or arrogant. (Keep in mind that i am a newly graduate engineer and not a manager or a director)

             
- **ATS Optimization:** Ensure the summary is ATS-friendly by including relevant keywords from the job description.
STRICT RULE : I AM AN AI and or Backend ENGINEER, DO NOT MENTION ANYTHING ELSE.
STRICT RULE 2: MEntion that im searching for a full-time position (CDI or CDD starting from november) in the summary, and also that i'm a rapid learner and highly intuitive.
STRICT RULE 3: DO NOT MENTION THE NAME OF THE COMPANY OR THE POSITION I AM APPLYING FOR.
- **Geographic flexibility:** Identify the locations implied in the job description and signal that I adapt easily to those environments (remote/hybrid/on-site), without naming the city explicitly so the text stays reusable.
- **Authenticity:** Keep a human, grounded tone—no exaggerated claims, only skills that appear in the LaTeX resume or are natural extensions of the same responsibilities.
### Output Format ###

Provide the professional summary as a standalone paragraph straight to the point and very concise, ready to be placed at the top of a CV.  
---        
             
---
CRUCIAL: The output should be in french. (its a french resume)
---
         
RETURN exactly one JSON object matching this schema (and nothing else):
{format_instructions}
''',
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])

    with open(latex, "r", encoding="utf-8") as file:
        current_resume = file.read()

    executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = executor.invoke(
        {
            "job_description": job_description,
            "agent_scratchpad": "",
            "LateXCode": current_resume,
        }
    )
    data = json.loads(raw_response["output"])
    return data["bullet_points"]
