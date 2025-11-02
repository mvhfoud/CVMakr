"""Agents responsible for extracting skill-oriented LaTeX fragments."""

from __future__ import annotations

import json
from typing import Any, List

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from cvmakr.utils.skills import MANDATORY_SKILLS, format_skill_categories


class _SkillCategory(BaseModel):
    title: str
    items: List[str]


class _SkillsResponse(BaseModel):
    categories: List[_SkillCategory]


def run_skills_agent(job_description: str, courses_skills_path: str, exclude_list: str) -> str:
    """Generate grouped competency lines ready for the LaTeX template."""

    parser = PydanticOutputParser(pydantic_object=_SkillsResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''
### Prompt ###
You are an HR-assistant.

TASK  
Read the job description in <JD>{job_description}</JD> **and** the latex rǸsumǸ in <CV>{courses_skills}</CV>.  
Return five themed categories of competencies that respect the quotas below. Output French labels and skills.

### Catégories & Quotas ###
1. Langages & Frameworks – 8 éléments essentiels (langages + frameworks principaux).
2. Data & Backend – 8 éléments (bases de données, DevOps, cloud, pipelines).
3. IA/ML – 6 éléments (bibliothèques, plateformes ou techniques IA/ML).
4. Soft Skills – 4 compétences comportementales pertinentes.

### Balance Rules ###
- Priorise les compétences structurantes pour le poste et ton profil (pas de gadgets de niche).
- Les compétences présentes dans le CV doivent représenter au moins 80% de chaque catégorie.
- Jusqu'à 20% peut provenir du JD si c'est une extension naturelle d'une compétence existante (ex. Docker → Docker Compose, Kubernetes → Helm). Note ces ajouts dans ta réflexion pour rester sous le seuil.
- Toujours inclure : C++, Javascript, Python, FASTAPI, Docker, Kubernetes, React, PostgreSQL, Redis, Pytorch, CUDA, Bash, GIT, GCP, Data Structures.

### Strict Rules ###
1. Chaque compétence doit apparaître textuellement dans le CV ou être une extension évidente d’une compétence prouvée.
2. Aucune invention d’outils ou de stacks contraires au CV.
3. Pas de titres de poste, uniquement des noms d’outils/technologies/aptitudes.
4. Pas de doublons (variantes incluses) et garde un total de 26 éléments maximum.
5. Pas de langues humaines ni de termes vagues (« software », « workflow », etc.).

### Output ###
Return **only** the JSON object that matches ce schéma :
{format_instructions}
''',
            ),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])

    with open(courses_skills_path, "r", encoding="utf-8") as file:
        courses_skills = file.read()

    executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = executor.invoke(
        {
            "job_description": job_description,
            "agent_scratchpad": "",
            "exclude_list": exclude_list,
            "courses_skills": courses_skills,
        }
    )
    data: Any = json.loads(raw_response["output"])
    parsed = _SkillsResponse(**data)
    return format_skill_categories(parsed.categories, mandatory=MANDATORY_SKILLS)


class _LegacyCoursesResponse(BaseModel):
    course_picks: str


def run_courses_agent(job_description: str, courses_skills: str, exclude_list: str) -> str:
    """Legacy course-selection agent retained for parity with the previous monolith."""

    parser = PydanticOutputParser(pydantic_object=_LegacyCoursesResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '''
You are a smart resume/ATS optimizer. I will give you:

1. A job description.
2. A list of courses or skills.
3. A list of courses or skills to exclude (either because they are irrelevant or too similar to others).

Your task is to:
- Identify which courses/skills are most relevant to the job.
- Remove any that overlap closely in meaning (except if they were different technologies of the same domaine eg: C++ and Java or Keras and Tensorflow ).
- If a course you genuinely possess appears in the job description with a slightly different spelling or spacing, adjust the term very minimally to match that ATS‑preferred form – e.g., use “Computer Vision” instead of “computervision”. This improves keyword matching while remaining truthful. Do not add or rename skills you cannot prove.
- Return exactly 7 to 8 max course/skill names, in order of relevance—no explanation, just the list.
- At least two of the five courses/skills should be related to AI/ML, Data Science or Software Engineering, and they should be FIRST in the list.
- The other two should be related to the job description and the courses/skills list.
- Do not include Languages (ex: French, english .. etc)

Here’s an example input:

<JOB DESCRIPTION>
{job_description}
</JOB DESCRIPTION>
         
<COURSE/SKILL LIST>
{courses_skills}
</COURSE/SKILL LIST>
             
<EXCLUDE LIST>
{exclude_list}
</EXCLUDE LIST>
         
---

Now, please process that input and output your five ATS-optimized picks.
             
---
CRUCIAL: The output should be in french. (its a french resume)
---
        
OUTPUT
Return one string in this exact format (course1, course2, course3, course4, course5) and nothing else:
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
            "courses_skills": courses_skills,
            "exclude_list": exclude_list,
        }
    )
    data: Any = json.loads(raw_response["output"])
    return data["course_picks"]
