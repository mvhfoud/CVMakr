"""Agents dedicated to project selection and skill verification."""

from __future__ import annotations

import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class _ProjectsResponse(BaseModel):
    latex_block: str


def projects_agent(projects_path: str, job_description: str) -> str:
    """Select and format the four most relevant projects for the given job."""

    parser = PydanticOutputParser(pydantic_object=_ProjectsResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a professional ATS-resume expert.  
Inputs:  
1. A list of my academic projects (title + full description and technologies on 'projects').  
2. A job description in `job_description`.

INSTRUCTIONS:
- Analyze the job description to extract its key skills, responsibilities, and keywords.
- From the projects list, select exactly **five** projects from the list that best match.
- Use the job description to identify the most relevant projects to highlight, in order of relevance.
- For each selected project, use the **verbatim** title. and 3 to 4 technologies (ITx) used in the project or in the job description and makes sense in the context
- **DO NOT** use any special characters or commands (like \\downarrow,\\times...) Stick with normal stuff.
- **CRUCIAL** If you make something up in the technicalities of a certain project, make sure it makes perfect sense technically.
- Try to include the technologies used in the project description. (not necessarily all of them, but at least two).
- Truthfulness rule: every technology must either appear word-for-word in the original project description or be a direct companion technology that engineers routinely pair with the same stack. Keep these inferred additions under 35% and note them in your chain-of-thought so you never drift into fabrication.
         

 - EXTREMELY STRICT RULE:  Output **Five** `\\cvitem(...)(...)` entries, **exactly** like this with the () replaced with accolades to be correctly read by latex:

         
\\cvitem (titre du projet)  (IT1. IT2. IT3. IT4)  # Replace the () with accolades to be read by latex
         
\\cvitem titre du projet IT1. IT2. IT3. IT4


\\cvitem titre du projet IT1. IT2. IT3. IT4


\\cvitem titre du projet IT1. IT2. IT3. IT4


\\cvitem titre du projet IT1. IT2. IT3. IT4

         
Projects list:
{projects}

Job description:
{job_description}
         
---
CRUCIAL: The output should be in french. (its a french resume)
---

RETURN exactly one JSON object matching this schema (and nothing else):
{format_instructions}
""",
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])

    with open(projects_path, "r", encoding="utf-8") as file:
        projects = file.read()

    executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw = executor.invoke(
        {
            "projects": projects,
            "job_description": job_description,
            "agent_scratchpad": "",
        }
    )
    output = json.loads(raw["output"])
    return output["latex_block"]


class _VerificationResponse(BaseModel):
    latex_block: str


def skills_verification(projects: str, job_description: str) -> str:
    """Verify and expand the competencies section against the job description."""

    parser = PydanticOutputParser(pydantic_object=_VerificationResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Goal �?" Modify the �?oCompǸtences�?? LaTeX section only

> **System**  
> You are an expert technical rǸsumǸ editor.  
> Your task is to **take (A) a plain-text job description and (B) the existing LaTeX �?oCompǸtences�?? section, then return one corrected LaTeX code block that replaces the original section.**  
> Do not touch any other part of the rǸsumǸ.

---

### Inputs

<<JOB_DESCRIPTION>> {job_description}<\<JOB_DESCRIPTION>>

<<LATEX_COMPETENCES_SECTION>>{projects}<\<LATEX_COMPETENCES_SECTION>>


markdown


---

### What you must do

1. **Fix LaTeX syntax**  
    * Ensure the LaTeX code is valid and compilable.
2. **Extract skills from the job description**  
   * Collect every concrete tool, language, framework, cloud provider, methodology mentioned.
   * Expand common abbreviations (e.g. *GCP* ��' *Google Cloud Platform*, *K8s* ��' *Kubernetes*).

3. **Merge & deduplicate**  
   * Add some skills that aren�?Tt already listed if you judge them to be necessary for the job (even if aren't explicitely mentionned). 
   * Remove duplicates (case-insensitive) across all categories.
   * You CAN NOT remove any skills that are already in the LaTeX section, but you can add new ones if you judge them necessary for the job.


4. If you don't find skills that match the job description, Add them.

5. Organise the output into exactly the following categories (in this order): Langages & Frameworks, Data & Backend, IA/ML, Soft Skills.
6. Each line must follow this pattern: `\\textbf{{Titre}} : compétence1, compétence2, ... \\\\`.
7. Ensure the block contains between 24 et 26 compétences uniques et inclut : C++, Python, FASTAPI, Docker, Kubernetes, React, PostgreSQL, Redis, Pytorch, CUDA, Bash, GIT.
8. JD-derived additions must remain ≤20% of the total and stay technically coherent with the CV.
9. **Return only the modified LaTeX section** – nothing else (no surrounding comments).
10. Don't use obviously copy-pasted text from the JD; rephrase where needed, especially for soft skills.

{format_instructions}
""",
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="o4-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=[], verbose=True)

    raw = executor.invoke(
        {
            "projects": projects,
            "job_description": job_description,
            "agent_scratchpad": "",
        }
    )
    output = json.loads(raw["output"])
    return output["latex_block"]
