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
Return **exactly 22 distinct competencies**, STRICTLY allocated as:

- 5 programming_languages ( e.g. Python, Java, C++ ... etc) **NOT FRAMEWORKS, LANGUAGES**
- 8 frameworks  
- 4 softwares 
- 3 soft_skills  

BALANCE RULE  
• Prioritise terms that appear in **both** <JD> and <CV>.  
• If the quota for a category is still short, fill the remaining slots with terms from <JD>.  
• If the quota is *still* short, use terms from <CV>.

STRICT RULES  
1. **Verbatim-only** – the exact string must appear in at least one source.  
2. **No titles** – discard any phrase containing: engineer, developer, architect, manager, lead, consultant, analyst, administrator, coordinator, specialist, director.  
3. **Single nouns** – no verbs, verb phrases, or bundled forms (e.g. write C, C++, Python — *not* “C/C++/Python”).  
4. **No placeholders** – omit vague terms such as “software”, “programming language”, “workflow”.  
5. **One per item** – split combo terms and remove duplicates; keep the most specific form. 
6. Exclude Languages (ex: French, english .. etc) 
7. ALWAYS INCLUDE C++, Python, FASTAPI, Docker, Kubernetes, React, PostgreSQL, Redis, Flask, Pytorch, CUDA.
8. **15 exactly, quotas exact** – do not exceed or fall short.
9. DO not repeat the same word in different forms (ex: "Python" and "Python3" are the same word, do not include both).
         
---

Now, please process that input and output your fifteen ATS-optimized picks.
        
---
CRUCIAL: The output should be in french. (its a french resume)
---
       
             
OUTPUT
Return one string in this exact format \cvtag{compétence 1} \cvtag{compétence 2} \cvtag{compétence 3}... and nothing else:
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
- Return exactly five course/skill names, in order of relevance—no explanation, just the list.
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
- Generate exactly {number} concise, ATS-optimized bullet points in French from the provided internship details.

Inputs:
1. Internship description (PROJECT/INTERNSHIP).
2. Job description (JOB DESCRIPTION).

Rules:
- List experiences in reverse chronological order.
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
2. **Professional Background:**  
   "{professionalbackground}"
3. **LateX Code of my resume (for context)** 
    "{LateXCode}"            

### Task ###

Using the information provided above, generate a concise and impactful professional summary for my CV.

### Guidelines ###

- **Length:** Limit the summary to 2–3 sentences.  
- **Tone:** Maintain a professional, confident tone.  
- **Content:**  
  - Highlight the most relevant skills and experiences that align with the job description.  
    
  - Use active language and strong action verbs (e.g., led, developed, implemented).  
  - Avoid generic phrases and clichés; focus on specific strengths and accomplishments.  
  - Don't be too confident or arrogant. (Keep in mind that i am a newly graduate engineer and not a manager or a director)

             
- **ATS Optimization:** Ensure the summary is ATS-friendly by including relevant keywords from the job description.
STRICT RULE : I AM AN INDUSTRIAL/AI and SOFTWARE ENGINEER, DO NOT MENTION ANYTHING ELSE.
STRICT RULE 2: MEntion that im searching for a full-time position (CDI or CDD starting from september or october) in the summary.
STRICT RULE 3: DO NOT MENTION THE NAME OF THE COMPANY OR THE POSITION I AM APPLYING FOR.
### Output Format ###

Provide the professional summary as a standalone paragraph, ready to be placed at the top of a CV.  
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

    with open(filename, "r", encoding="utf-8") as file:
        professionalbackground = file.read()

    with open(filename2, "r", encoding="utf-8") as file:
        current_resume = file.read()

    agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
    raw_response = agent_executor.invoke({
        "job_description": job_description,
        "agent_scratchpad": "",
        "professionalbackground": professionalbackground,
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
    Transform LaTeX-style bullets marked with '-*' into LaTeX item syntax.
    The first bullet becomes '\\item {', and subsequent ones become '} \\item {'.
    A single closing '}' is added at the end.

    :param text: Multiline string with bullets marked as '-* bullet'
    :return: Transformed LaTeX string
    """
    lines = text.strip().splitlines()
    result = []

    for i, line in enumerate(lines):
        bullet_content = re.sub(r'^-\*\s*', '', line)
        if i == 0:
            result.append(f'\\item {{{bullet_content}')
        else:
            result.append(f'}} \\item {{{bullet_content}')
    
    return '\n'.join(result) + '}'


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
- For each selected project, use the **verbatim** title. and 4 technologies (ITx) used in the project (you can include one that existed only in the job description and not the project)
- **DO NOT** use any special characters or commands (like \downarrow,\times...) Stick with normal stuff.
- **CRUCIAL** If you make something up in the technicalities of a certain project, make sure it makes perfect sense technically.
- Try to include the technologies used in the project description. (not necessarily all of them, but at least two).
- EXTREMELY STRICT RULE:  Output **Four** `\item` entries, **exactly** like this:

         
\cvitem{titre du projet}{IT1. IT2}

\cvitem{titre du projet}{IT1. IT2}
         
\cvitem{titre du projet}{IT1. IT2}

\cvitem{titre du projet}{IT1. IT2}
         
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

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)
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
Rédige une lettre de motivation (en français) au format JSON strict, ultra-concis et percutant, en respectant la méthode SHARK.

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
1. Analyse !**job_description**! : isole exactement **3 à 4 compétences clés** (copie les mots tels quels).
2. Parcours !**experiences**! et !**projects**! : sélectionne seulement les exemples les plus parlants ; ignore le reste.
3. Structure la lettre en **12 – 15 phrases** :
   • *Situation* (1) – qui je suis + pourquoi ce poste.  
   • *Hindrance* (1-2) – défi majeur du rôle.  
   • *Action + Résultat* – 1 phrase par compétence (impact quantifié).  
   • *Kick-off* (1) – demande d’entretien énergique.  
4. Aucune salutation initiale, aucune formule de politesse finale, aucune signature.
5. Ton : professionnel, énergique, déterminé, humble.
6. Recherche web :  
   • Si le nom de l’entreprise n’apparaît pas dans !**job_description**!, effectue 1 recherche ciblée (site officiel + communiqué récent) et insère **une** donnée factuelle (levée de fonds, produit lancé, etc.).  
   • Abandonne si rien d’exploitable en 60 s.
7. Longueur totale : **≤ 1 500 caractères** (espaces compris).

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



#------------------

# Configuration
OUTPUT_DIR = "resume"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("logo.png")
    with col2:
        st.title("Résumé & Motivation Letter Generator (LaTeX)")

    # Inputs
    job_description = st.text_area("Paste the job description here:", height=200)
    offer_link      = st.text_input("Paste the job offer URL here:")
    gen_resume      = st.button("Generate Résumé")
    gen_letter      = st.checkbox("Generate Motivation Letter")

    # State for regeneration
    if 'letter_output' not in st.session_state:
        st.session_state.letter_output = ""
    if 'gen_letter_done' not in st.session_state:
        st.session_state.gen_letter_done = False

    if gen_resume:
        if not job_description.strip():
            st.error("Please enter a job description before generating.")
            st.stop()

        load_dotenv()
        timestamp       = datetime.now().strftime("%Y%m%d_%H%M%S")
        resume_filename = f"{timestamp}_CV_Youssef.txt"
        letter_filename = f"{timestamp}_ML_Youssef.txt"

        # —— 1) Generate Motivation Letter FIRST ——
        if gen_letter:
            st.session_state.gen_letter_done = True
            with st.spinner("Generating motivation letter…"):
                st.session_state.letter_output = escape_latex_special_chars(motivation_letter_agent(
                    "experiences.txt",
                    "projects.txt",
                    "personalaspirations.txt",
                    job_description
                ))

        if st.session_state.gen_letter_done:
            st.success("Motivation letter ready: {}".format(letter_filename))
            st.subheader("Motivation Letter Text")
            st.text_area(
                "", st.session_state.letter_output,
                height=300, key="letter_area"
            )
            # Regenerate button
            if st.button("Regenerate Lettre de Motivation"):
                with st.spinner("Regenerating motivation letter…"):
                    st.session_state.letter_output = escape_latex_special_chars(motivation_letter_agent(
                        "experiences.txt",
                        "projects.txt",
                        "personalaspirations.txt",
                        job_description
                    ))
                st.text_area(
                    "", st.session_state.letter_output,
                    height=300, key="letter_area"
                )

            # Save letter file
            letter_path = os.path.join(OUTPUT_DIR, letter_filename)
            with open(letter_path, 'w', encoding='utf-8') as f:
                f.write(st.session_state.letter_output)

        # —— 2) Generate Résumé ——
        resume_path = os.path.join(OUTPUT_DIR, resume_filename)
        shutil.copy("Latexoriginalexample.txt", resume_path)

        total_steps = 3 + 4 + 3
        step = 0
        progress = st.progress(0)

        # Courses
        # exclude_list = ""
        # for i in range(3):
        #     st.write(f"Processing course {i+1}/3…")
        #     matieres = parse_first_line_column(i+1)
        #     output = run_courses_agent(job_description, matieres, exclude_list)
        #     safe   = escape_latex_special_chars(output)
        #     replace_placeholder_in_file_inplace(resume_path, i+1, safe)
        #     exclude_list += output + ", "
        #     step += 1
        #     progress.progress(step/total_steps)

        # Internships
        internships = [
            ("Experience_Dassault.txt", 3),
            ("Experience_Aimovement.txt", 3),
            ("Experience_TNC.txt", 2),
            ("Experience_Lear.txt", 2),
        ]
        for idx, (fn, count) in enumerate(internships, start=1):
            st.write(f"Processing internship {idx}/4…")
            raw = run_internship_agent(job_description, fn, count)
            cur = transform_bullets(raw)
            smth=[]
            cur = escape_latex_special_chars(cur)
            replace_placeholder_in_file_inplace(resume_path, idx+3, cur)
            step += 1
            progress.progress(step/total_steps)

        # Projects
        st.write("Processing projects…")
        raw_projects = projects_agent("projects.txt", job_description)
        safe_projects = escape_latex_special_chars(raw_projects)
        replace_placeholder_in_file_inplace(resume_path, 8, safe_projects)
        step += 1
        progress.progress(step/total_steps)

        # Skills
        st.write("Processing skills…")
        skills_tex = run_skills_agent(job_description, "Latexoriginalexample.txt", "")
        replace_placeholder_in_file_inplace(resume_path, 9, escape_latex_special_chars(skills_tex))
        step += 1
        progress.progress(step/total_steps)

        # Summary
        st.write("Processing summary…")
        summary_tex = run_summary_agent(job_description, resume_path)
        replace_placeholder_in_file_inplace(resume_path, 0, escape_latex_special_chars(summary_tex))
        step += 1
        progress.progress(step/total_steps)

        # Display and download 
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_tex = f.read()

        st.success(f"Résumé ready: {resume_filename}")
        st.download_button(
            label="Download LaTeX résumé",
            data=resume_tex,
            file_name=resume_filename,
            mime="text/plain"
        )
        st.subheader("LaTeX Code (Résumé)")
        st.text_area("", resume_tex, height=300)

        # Log to applications.csv
        apps_csv = os.path.join(OUTPUT_DIR, "applications.csv")
        if not os.path.exists(apps_csv):
            with open(apps_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["link", "date", "resume", "coverletter", "marker"])

        today = datetime.now().strftime("%Y-%m-%d")
        with open(apps_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                offer_link,
                today,
                resume_filename,
                (letter_filename if st.session_state.gen_letter_done else ""),
                "Sent"
            ])

if __name__ == "__main__":
    main()