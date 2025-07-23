from pdb import run
import string
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
import json
import csv
import re
import streamlit as st
import os
import shutil
from datetime import datetime
import asyncio
import subprocess
from langchain.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from PIL import Image





# Updated agent to enforce category quotas and noun-only extraction

def run_skills_agent(job_description, courses_skills, exclude_list):


    class ResearchResponse2(BaseModel):
        course_picks: str  # List of skills/courses

    parser2 = PydanticOutputParser(pydantic_object=ResearchResponse2)

    prompt2 = ChatPromptTemplate.from_messages(
        [
            ("system", '''
### Prompt ###  
You are an HR-assistant.

TASK  
Read the job description in <JD>{job_description}</JD> **and** the latex résumé in <CV>{courses_skills}</CV>.  
Return **exactly between 25 and 30 max distinct competencies**, STRICTLY allocated as:

-CRUCIAL: The competencies that figure in the resume must also figure in this list ideally 75\% 25\%  can then fill the rest from the job description(for compatiblity purposes and to reduce skepticism from recruiters)
             
- 7 programming_languages ( e.g. Python, Java, C++ ... etc) **NOT FRAMEWORKS, LANGUAGES**
- 8 frameworks  
- 6 softwares 
- 2 soft_skills  
- 2 wild cards (be creative, except languages)
             
BALANCE RULE  
ALWAYS INCLUDE C++, Python, FASTAPI, Docker, Kubernetes, React, PostgreSQL, Redis, Pytorch, CUDA, Bash, GIT.
• Prioritise terms that appear in **both** <JD> and <CV>.  
• If the quota for a category is still short, fill the remaining slots with terms with 75\% of skills from <CV> and 25\% from <JD>.  


STRICT RULES  
1. **Verbatim-only** – the exact string must appear in at least one source.  
2. **No titles** – discard any phrase containing: engineer, developer, architect, manager, lead, consultant, analyst, administrator, coordinator, specialist, director.  
3. **Single nouns** – no verbs, verb phrases, or bundled forms (e.g. write C, C++, Python — *not* “C/C++/Python”).  
4. **No placeholders** – omit vague terms such as “software”, “programming language”, “workflow”.  
5. **One per item** – split combo terms and remove duplicates; keep the most specific form. 
6. Exclude Languages (ex: French, english .. etc) 
7. ALWAYS INCLUDE C++, Python, FASTAPI, Docker, Kubernetes, React, PostgreSQL, Redis, Pytorch, CUDA, Bash, GIT.
8. **15 exactly, quotas exact** – do not exceed or fall short.
9. DO not repeat the same word in different forms (ex: "Python" and "Python3" are the same word, do not include both).
             10. Never include Node.js
         
---

Now, please process that input and output your fifteen ATS-optimized picks.
        
---
CRUCIAL: The output should be in french. (its a french resume)
---
       
             
OUTPUT
Return one string in this exact format \cvtag(compétence 1) \cvtag(compétence 2) \cvtag(compétence 3)... and nothing else:  # Replace the () with accolades to be read by latex
{format_instructions}
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser2.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)

    agent2 = create_tool_calling_agent(
        llm=llm,
        prompt=prompt2,
        tools=[]
    )
    with open(courses_skills, "r", encoding="utf-8") as file:
        courses_skills = file.read()

    agent_executor2 = AgentExecutor(agent=agent2, tools=[], verbose=True)
    raw_response_2 = agent_executor2.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "exclude_list": exclude_list,
        "courses_skills": courses_skills
    })
    data = json.loads(raw_response_2["output"])
    course_picks = data["course_picks"]
    return course_picks


### Second agent ###
def run_courses_agent(job_description, courses_skills, exclude_list):


    class ResearchResponse2(BaseModel):
        course_picks: str  # List of skills/courses

    parser2 = PydanticOutputParser(pydantic_object=ResearchResponse2)

    prompt2 = ChatPromptTemplate.from_messages(
        [
            ("system", '''
You are a smart resume/ATS optimizer. I will give you:

1. A job description.
2. A list of courses or skills.
3. A list of courses or skills to exclude (either because they are irrelevant or too similar to others).

Your task is to:
- Identify which courses/skills are most relevant to the job.
- Remove any that overlap closely in meaning (except if they were different technologies of the same domaine eg: C++ and Java or Keras and Tensorflow ).
- If a course you genuinely possess appears in the job description with a slightly different spelling or spacing, adjust the term very minimally to match that ATS‑preferred form — e.g., use “Computer Vision” instead of “computervision”. This improves keyword matching while remaining truthful. Do not add or rename skills you cannot prove.
- Return exactly 7 to 8 max course/skill names, in order of relevance—no explanation, just the list.
- Atleast two of the five courses/skills should be related to AI/ML, Data Science or Software Engineering, and they should be FIRST in the list.
- The other two should be related to the job description and the courses/skills list.
- The last one should be a wildcard related to the whole theme of the list.
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
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser2.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)

    agent2 = create_tool_calling_agent(
        llm=llm,
        prompt=prompt2,
        tools=[]
    )

    agent_executor2 = AgentExecutor(agent=agent2, tools=[], verbose=True)
    raw_response_2 = agent_executor2.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "courses_skills": courses_skills,
        "exclude_list": exclude_list
    })
    data = json.loads(raw_response_2["output"])
    course_picks = data["course_picks"]
    return course_picks

def run_internship_agent(job_description, filename, number):
    # This agent is used to generate ATS-optimized bullet points from internship experience and job description.


    
    class ResearchResponse(BaseModel):
        bullet_points: str # List of skills/courses

    parser = PydanticOutputParser(pydantic_object=ResearchResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", '''
You are an expert in optimizing resumes for ATS (Applicant Tracking Systems). 

Your task:
- Generate exactly {number} concise, ATS-optimized bullet points in French from the provided internship details, after reading the internship description and the job description and understanding it fully, so you don't make stuff up.

Inputs:
1. Internship description (PROJECT/INTERNSHIP).
2. Job description (JOB DESCRIPTION).

Rules:
- Clearly state tasks and accomplishments respecting the original content and structure.
- Highlight skills and achievements that best match the job description.
- Begin each bullet point with a strong, past-tense action verb (e.g., « développé »).
- Quantify achievements where possible (once or twice max).
- Expand abbreviations at first use (e.g., « Tonnes métriques (TM) »).
- Use synonyms rather than directly copying phrases from the job description.
- Bullet points must represent the essence of the internship, not random matches.
- Maximum one line per bullet point.
- Do not include personal details (name, contact information, etc.).
- Output each bullet point preceded by "-*".
CRUCIAL:
- Keep the original workflow of what i did during the internship.

Here’s your structured input:

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
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions(),
                  number=number)

    llm = ChatOpenAI(model="o3-mini")

    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=[]
    )

    with open(filename, "r", encoding="utf-8") as file:
        internship = file.read()

    agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = agent_executor.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "internship": internship,
        "number": number
    })
    data = json.loads(raw_response["output"])
    bullet_points_str = data["bullet_points"]
    print('used:'+ str(number) + ' bullet points')
    return bullet_points_str


def run_summary_agent(job_description,latex):
    # This agent is used to generate ATS-optimized bullet points from internship experience and job description.


    class ResearchResponse(BaseModel):
        bullet_points: str # List of skills/courses

    parser = PydanticOutputParser(pydantic_object=ResearchResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", '''
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

- **Length:** Limit the summary to 2-3 sentences.  
- **Tone:** Maintain a professional, confident tone.  
- **Content:**  
  - Highlight the most relevant skills and experiences that align with the job description.  
    
  - Use active language and strong action verbs (e.g., led, developed, implemented).  
  - Avoid generic phrases and clichés; focus on specific strengths and accomplishments.  
  - Don't be too confident or arrogant. (Keep in mind that i am a newly graduate engineer and not a manager or a director)

             
- **ATS Optimization:** Ensure the summary is ATS-friendly by including relevant keywords from the job description.
STRICT RULE : I AM AN AI and or SOFTWARE ENGINEER, DO NOT MENTION ANYTHING ELSE.
STRICT RULE 2: MEntion that im searching for a full-time position (CDI or CDD starting from september or october) in the summary, and also that i'm a rapid learner and highly intuitive.
STRICT RULE 3: DO NOT MENTION THE NAME OF THE COMPANY OR THE POSITION I AM APPLYING FOR.
### Output Format ###

Provide the professional summary as a standalone paragraph straight to the point and very concise, ready to be placed at the top of a CV.  
---        
             
---
CRUCIAL: The output should be in french. (its a french resume)
---
             
OUTPUT
Return one JSON object for this schema and nothing else:
{format_instructions}
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="o3-mini")

    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=[]
    )

    filename= "personalaspirations.txt"
    filename2= latex


    with open(filename2, "r", encoding="utf-8") as file:
        current_resume = file.read()

    agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = agent_executor.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "LateXCode": current_resume
    })
    data = json.loads(raw_response["output"])
    bullet_points_str = data["bullet_points"]
    return bullet_points_str






def parse_first_line_column(i: int) -> str:
        with open('myskills.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            first_line = next(reader, None)
            if first_line is None:
                raise ValueError("CSV file is empty")
            if i < 1 or i > len(first_line):
                raise IndexError("Column index out of range")
            return first_line[i - 1]

def replace_placeholder_in_file_inplace(file_path: str, target_int: int, replacement: str) -> None:
    """
    Lit le fichier LaTeX, remplace les tokens '??*<n>*??' où <n> == target_int par replacement,
    puis écrase le contenu du même fichier avec le résultat.

    :param file_path: chemin vers le fichier .txt contenant le code LaTeX
    :param target_int: entier à chercher dans les placeholders
    :param replacement: chaîne à substituer au placeholder correspondant
    """
    # motif pour capturer '??*123*??', avec le groupe 1 contenant '123'
    pattern = re.compile(r'\?\?\*(\d+)\*\?\?')

    def _repl(m: re.Match) -> str:
        num = int(m.group(1))
        if num == target_int:
            return replacement
        return m.group(0)

    # lecture + remplacement
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    new_text = pattern.sub(_repl, text)

    # écriture en place
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_text)





def transform_bullets(text: str) -> str:
    """
    Remove all line breaks and replace LaTeX-style bullets marked with '-*':
    - At the very start, insert '\\item{'
    - The first '-*' becomes '} \\item{'
    - Subsequent '-*' become '\\item{'
    - Ensure each '\\item{' is on its own line (preceded by a newline)
    - At the end of the output text, add '}'.

    :param text: String containing '-*' bullet markers and possible line breaks.
    :return: Transformed string with correct bullet replacements.
    """
    # 1. Remove all existing newlines
    flat = text.replace('\n', ' ')
    
    # 2. Split on '-*', strip, and discard empties
    parts = [p.strip() for p in re.split(r'-\*\s*', flat) if p.strip()]
    if not parts:
        return ''
    
    # 3. Start with a leading newline + first \item{
    output = "\n\\item{" + parts[0]
    
    # 4. Insert bullets for each subsequent part
    for i, part in enumerate(parts[1:], start=1):
        if i == 1:
            # first bullet uses the closing brace then a new \item{
            output += "} \n\\item{" + part
        else:
            # later bullets just start a new \item{
            output += "} \n\\item{" + part
    
    # 5. Close the very last item
    output += "}"
    return output






def escape_latex_special_chars(text: str) -> str:
    """
    Escapes LaTeX special characters in a string by prefixing them with a backslash.
    Useful for safely inserting text into LaTeX documents.
    """
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }

    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    
    return text

def wrapper_agent(internship, job_description):


    
    class ResearchResponse(BaseModel):
        bullet_points: str # List of skills/courses

    parser = PydanticOutputParser(pydantic_object=ResearchResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", '''
You are a professional ATS resume expert. Your inputs are:
    1. A text file containing one of my project or internship experiences described exhaustively (or my summary).
    2. A job description for the role I’m applying to.

INSTRUCTIONS:
            - Read the bullet points as they are and do not change their content or structure. Your task is only to identify important technical or impactful words (such as tools, actions, or results) and wrap at least one per bullet point using the LaTeX \textbf command for emphasis.
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
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions(),
                  )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)

    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=[]
    )


    agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = agent_executor.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "internship": internship,
    })
    data = json.loads(raw_response["output"])
    bullet_points_str = data["bullet_points"]
    return bullet_points_str

def projects_agent(projects: str, job_description: str) -> str:
    class ProjectsResponse(BaseModel):
        latex_block: str  # will contain one \\begin{itemize}… block

    parser = PydanticOutputParser(pydantic_object=ProjectsResponse)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
You are a professional ATS-resume expert.  
Inputs:  
1. A list of my academic projects (title + full description and technologies on 'projects').  
2. A job description in `job_description`.

INSTRUCTIONS:
- Analyze the job description to extract its key skills, responsibilities, and keywords.
- From the projects list, select exactly **four** that best match.
- Use the job description to identify the most relevant projects to highlight, in order of relevance.
- For each selected project, use the **verbatim** title. and 3 to 4 technologies (ITx) used in the project or in the job description and makes sense in the context
- **DO NOT** use any special characters or commands (like \downarrow,\times...) Stick with normal stuff.
- **CRUCIAL** If you make something up in the technicalities of a certain project, make sure it makes perfect sense technically.
- Try to include the technologies used in the project description. (not necessarily all of them, but at least two).
         

- EXTREMELY STRICT RULE:  Output **Four** `\item` entries, **exactly** like this:

         
\cvitem (titre du projet)  (IT1. IT2. IT3. IT4)  # Replace the () with accolades to be read by latex

\cvitem titre du projet  IT1. IT2. IT3. IT4
         
\cvitem titre du projet  IT1. IT2. IT3. IT4

\cvitem titre du projet  IT1. IT2. IT3. IT4

\cvitem titre du projet  IT1. IT2. IT3. IT4

         
Projects list:
{projects}

Job description:
{job_description}
         
---
CRUCIAL: The output should be in french. (its a french resume)
---

RETURN exactly one JSON object matching this schema (and nothing else):
{format_instructions}
"""),
        ("placeholder", "{agent_scratchpad}")
    ]).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=[], verbose=True)

    with open(projects, "r", encoding="utf-8") as file:
        projects = file.read()

    raw = executor.invoke({
        "projects": projects,
        "job_description": job_description,
        "agent_scratchpad": ""
    })
    output = json.loads(raw["output"])
    string = output["latex_block"]
    return string

def skills_verification(projects: str, job_description: str) -> str:
    class ProjectsResponse(BaseModel):
        latex_block: str  # will contain one \\begin{itemize}… block

    parser = PydanticOutputParser(pydantic_object=ProjectsResponse)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
Goal — Modify the “Compétences” LaTeX section only

> **System**  
> You are an expert technical résumé editor.  
> Your task is to **take (A) a plain-text job description and (B) the existing LaTeX “Compétences” section, then return one corrected LaTeX code block that replaces the original section.**  
> Do not touch any other part of the résumé.

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
   * Expand common abbreviations (e.g. *GCP* → *Google Cloud Platform*, *K8s* → *Kubernetes*).

3. **Merge & deduplicate**  
   * Add some skills that aren’t already listed if you judge them to be necessary for the job (even if aren't explicitely mentionned). 
   * Remove duplicates (case-insensitive) across all categories.
   * You CAN NOT remove any skills that are already in the LaTeX section, but you can add new ones if you judge them necessary for the job.


4. If you don't find skills that match the job description, Add them.
         
         
5. **Return only the modified LaTeX section** — nothing else. and remove the \% Compétences at first.
6. Make sure it's over 20 skills min and 25 max.
         
{format_instructions}
"""),
        ("placeholder", "{agent_scratchpad}")
    ]).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="o4-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=[], verbose=True)



    raw = executor.invoke({
        "projects": projects,
        "job_description": job_description,
        "agent_scratchpad": ""
    })
    output = json.loads(raw["output"])
    string = output["latex_block"]
    return string

def motivation_letter_agent(experiences: str, projects: str, background: str, job_description: str) -> str:
    """
    Génère une lettre de motivation personnalisée en français pour un poste donné, concise et percutante.

    Args:
        experiences: Chemin vers le fichier texte contenant la liste de mes expériences professionnelles.
        projects: Chemin vers le fichier texte contenant la liste de mes projets académiques.
        background: Chemin vers le fichier texte décrivant mon parcours et mes atouts.
        job_description: Description complète du poste cible.

    Returns:
        Une lettre de motivation au format texte brut.
    """
    class MotivationResponse(BaseModel):
        letter_text: str  # Contiendra la lettre de motivation en français

    # Parseur pour forcer la sortie JSON selon le schéma
    parser = PydanticOutputParser(pydantic_object=MotivationResponse)

    # Construction du prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
OBJECTIF
Rédige une lettre de motivation (en français), ultra-concis et percutant, en respectant la méthode SHARK.

ENTRÉES  
Chaque bloc de texte brut est encadré par des accolades portant son nom :

…!**experiences**!
         
{experiences}
         
…!**projects**!
         
{projects}
         
…!**background**!
         
{background}
         
…!**job_description**!
         
{job_description}
         
…

RÈGLES

1. Analyse le ton et l’énergie du !**job_description**! et reproduis-les dès la première phrase et tout au long de la lettre (ex: dynamique, ambitieux, innovant).

2. Priorise tes compétences actuelles et ta motivation forte, sans te limiter à décrire tes expériences passées. Utilise-les pour illustrer ta capacité à relever les défis du poste.

3. Effectue une recherche rapide sur l’entreprise (site officiel, actualités) pour identifier une valeur clé ou un fait récent. Intègre cet élément pour montrer ta compréhension et ton alignement avec leur culture.

4. Structure la lettre selon SHARK en 12-15 phrases :

   - Situation : qui tu es + pourquoi ce poste, avec le ton du job description.
   - Hindrance : défi principal du poste.
   - Action + Résultat : 1 phrase par compétence, illustrée par tes capacités actuelles.
   - Kick-off : phrase de clôture énergique, montrant ta détermination féroce à convaincre en entretien.

5. Longueur totale : ≤ 1 500 caractères (espaces compris).

6. Ton : professionnel, énergique, déterminé, humble, en miroir avec l’énergie du job description.

7. Aucune salutation initiale, aucune formule de politesse finale, aucune signature.

8. Longueur totale : **≤ 1 500 caractères** (espaces compris).

SORTIE  
Retourne **exactement** cet objet JSON (aucun texte en dehors) :
         
RETURN exactement un objet JSON selon ce schéma (et rien d'autre) :
{format_instructions}
"""),
        ("placeholder", "{agent_scratchpad}")
    ]).partial(format_instructions=parser.get_format_instructions())

    # Préparation de l'outil de recherche web avec SerpAPI
    serp = SerpAPIWrapper()
    web_search_tool = Tool(
        name="web_search",
        func=serp.run,
        description="Utilisez pour rechercher des informations sur l'entreprise cible lorsque nécessaire via SerpAPI."
    )
    tools = [web_search_tool]

    # Initialisation LLM et agent
    llm = ChatOpenAI(model="gpt-4.1-mini")
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    # Lecture des fichiers d'entrée
    with open(experiences, "r", encoding="utf-8") as file:
        experiences_content = file.read()
    with open(projects, "r", encoding="utf-8") as file:
        projects_content = file.read()
    with open(background, "r", encoding="utf-8") as file:
        background_content = file.read()

    # Invocation de l'agent
    raw = executor.invoke({
        "experiences": experiences_content,
        "projects": projects_content,
        "background": background_content,
        "job_description": job_description,
        "agent_scratchpad": ""
    })
    output = json.loads(raw["output"])
    return output["letter_text"]




# if __name__ == "__main__":



#     load_dotenv()


#     latex_file= "Latexoriginalexample.txt"
#     job_description= input('job description: ')

#     #Cours notables:

#     exclude_list = ""

#     for i in range(3):
#         matieres = parse_first_line_column(i+1)
#         output= run_courses_agent(job_description, matieres, exclude_list)
#         current= output
#         current= escape_latex_special_chars(current)
#         replace_placeholder_in_file_inplace(latex_file, i+1, current)
#         exclude_list += output + ", "
    
    
#     ###Internships:
#     for i in range(4):
#         if i==0:
#             filename= "Experience_Dassault.txt"
#             j=3
#         elif i==1:
#             filename= "Experience_Aimovement.txt"
#             j=3
#         elif i==2:
#             filename= "Experience_TNC.txt"
#             j=2
#         elif i==3:
#             filename= "Experience_Lear.txt"
#             j=2
        
#         current=transform_bullets(run_internship_agent(job_description, filename, j))


#         current= wrapper_agent(current, job_description)
#         current= escape_latex_special_chars(current)

#         replace_placeholder_in_file_inplace(latex_file, i+4, current)
#         print("Experience " + str(i+1) + " done")
#         print(current)

#     ## ###Projects:
#     filename= "projects.txt"
#     current= projects_agent( filename, job_description)
#     current= escape_latex_special_chars(current)
#     print(current)
#     replace_placeholder_in_file_inplace(latex_file, 8, current)

#     print("Projects done")

#     exclud= ""


#     print(replace_placeholder_in_file_inplace(latex_file, 9, run_skills_agent(job_description, "latexoriginalexample.txt", exclud))) #VALIDATED

#     print(replace_placeholder_in_file_inplace(latex_file,0,run_summary_agent(job_description))) #VALIDATED




import os
import shutil
from datetime import datetime
import streamlit as st


# --- Google Drive & Sheets configuration via OAuth 2.0 ---
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

CLIENT_SECRETS_FILE = os.getenv('CLIENT_SECRETS_FILE')
TOKEN_PATH = 'token.json'


def oauth_creds():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
    return creds


def init_services():
    creds = oauth_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_client = gspread.authorize(creds)
    return drive_service, sheets_client


def upload_to_drive(file_path, folder_id):
    drive_service, _ = init_services()
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='text/plain')
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()


def mount_drive():
    return os.getcwd()


def append_to_sheet(row: list):
    """
    Append a row to Google Sheet:
      A: offer link
      B: date (will be bolded)
      C: resume filename
      D: status (dropdown with colors pre-configured in the Sheet)
    """
    _, sheets_client = init_services()
    sheet = sheets_client.open_by_key(SHEET_ID).sheet1
    # Append row with 4 columns
    sheet.append_row(row, value_input_option='USER_ENTERED')
    # Get the index of the new row
    all_values = sheet.get_all_values()
    row_idx = len(all_values)
    # Bold the date in column B
    cell_label = f'B{row_idx}'
    sheet.format(cell_label, {'textFormat': {'bold': True}})
    # Note: Ensure you have set up a dropdown (data validation) and conditional formatting
    # for column D (status) in your Google Sheet UI. This code will insert the default status,
    # and the colors will apply as per your sheet's conditional formatting rules.
    # The dropdown options should be: "Application Sent", "Got Interview", "Rejected".


SHEET_ID = os.getenv('SHEET_ID')
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')


def main():
    drive_base = mount_drive()
    DRIVE_OUTPUT_DIR = os.path.join(drive_base, 'tmp')
    os.makedirs(DRIVE_OUTPUT_DIR, exist_ok=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image('logo.png')
    with col2:
        st.title('Résumé & Motivation Letter Generator (LaTeX)')

    job_description = st.text_area('Paste the job description here:', height=200)
    offer_link = st.text_input('Paste the job offer URL here:')
    gen_resume = st.button('Generate Résumé')
    gen_letter = st.checkbox('Generate Motivation Letter')

    if 'letter_output' not in st.session_state:
        st.session_state.letter_output = ''
    if 'gen_letter_done' not in st.session_state:
        st.session_state.gen_letter_done = False

    if gen_resume:
        if not job_description.strip():
            st.error('Please enter a job description before generating.')
            st.stop()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        resume_filename = f"{timestamp}_CV_Youssef.txt"
        letter_filename = f"{timestamp}_ML_Youssef.txt"

        if gen_letter:
            st.session_state.gen_letter_done = True
            with st.spinner('Generating motivation letter…'):
                st.session_state.letter_output = escape_latex_special_chars(
                    motivation_letter_agent(
                        'experiences.txt',
                        'projects.txt',
                        'personalaspirations.txt',
                        job_description
                    )
                )

        if st.session_state.gen_letter_done:
            st.success(f'Motivation letter ready: {letter_filename}')
            st.subheader('Motivation Letter Text')
            st.text_area('', st.session_state.letter_output, height=300)
            if st.button('Regenerate Lettre de Motivation'):
                with st.spinner('Regenerating motivation letter…'):
                    st.session_state.letter_output = escape_latex_special_chars(
                        motivation_letter_agent(
                            'experiences.txt',
                            'projects.txt',
                            'personalaspirations.txt',
                            job_description
                        )
                    )
                st.text_area('', st.session_state.letter_output, height=300)

        resume_path = os.path.join(DRIVE_OUTPUT_DIR, resume_filename)
        shutil.copy('Latexoriginalexample2.txt', resume_path)

        total_steps = 10
        step = 0
        progress = st.progress(0)

        exclude_list = ''
        # for i in range(3):
        #     st.write(f'Processing course {i+1}/3…')
        #     matieres = parse_first_line_column(i+1)
        #     output = run_courses_agent(job_description, matieres, exclude_list)
        #     safe = escape_latex_special_chars(output)
        #     replace_placeholder_in_file_inplace(resume_path, i+1, safe)
        #     exclude_list += output + ', '
        #     step += 1
        #     progress.progress(step/total_steps)

        internships = [
            ('Experience_Dassault.txt', 1),
            ('Experience_Aimovement.txt', 1),
            ('Experience_TNC.txt', 2),
            ('Experience_Lear.txt', 1),
        ]
        for idx, (fn, count) in enumerate(internships, start=1):
            st.write(f'Processing internship {idx}/4…')
            raw = run_internship_agent(job_description, fn, count)
            cur = escape_latex_special_chars(transform_bullets(raw))
            replace_placeholder_in_file_inplace(resume_path, idx+3, cur)
            step += 1
            progress.progress(step/total_steps)

        st.write('Processing projects…')
        raw_projects = projects_agent('projects.txt', job_description)
        raw_projects = wrapper_agent(raw_projects, job_description)
        safe_projects = escape_latex_special_chars(raw_projects)
        replace_placeholder_in_file_inplace(resume_path, 8, safe_projects)
        step += 1
        progress.progress(step/total_steps)

        st.write('Processing skills…')
        skills_tex = run_skills_agent(job_description, resume_path, '')
        skills_tex = skills_verification(skills_tex, job_description)
        skills_tex = escape_latex_special_chars(skills_tex)

        replace_placeholder_in_file_inplace(resume_path, 9, skills_tex)
        step += 1
        progress.progress(step/total_steps)

        st.write('Processing summary…')
        summary_tex = run_summary_agent(job_description, resume_path)
        replace_placeholder_in_file_inplace(resume_path, 0, escape_latex_special_chars(summary_tex))
        step += 1
        progress.progress(step/total_steps)

        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_tex = f.read()
        st.success(f'Resumé ready: {resume_filename}')
        st.download_button(label='Download LaTeX résumé', data=resume_tex, file_name=resume_filename, mime='text/plain')
        st.subheader('LaTeX Code (Résumé)')
        st.text_area('', resume_tex, height=300)

        upload_to_drive(resume_path, FOLDER_ID)
        if st.session_state.gen_letter_done:
            letter_path = os.path.join(DRIVE_OUTPUT_DIR, letter_filename)
            with open(letter_path, 'w', encoding='utf-8') as f:
                f.write(st.session_state.letter_output)
            upload_to_drive(letter_path, FOLDER_ID)

        today = datetime.now().strftime('%Y-%m-%d')
        row = [offer_link, today, resume_filename, 'Application Sent']
        append_to_sheet(row)


if __name__ == '__main__':
    load_dotenv()
    main()
