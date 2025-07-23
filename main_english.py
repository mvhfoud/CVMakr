from pdb import run
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
import json
import csv
import re




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
Return **exactly 15 distinct competencies**, allocated as:

- 5 programming_languages ( e.g. Python, Java, C++ ... etc) **NOT FRAMEWORKS, LANGUAGES**
- 3 frameworks  
- 4 software  
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
7. **15 exactly, quotas exact** – do not exceed or fall short.
             
         
---

Now, please process that input and output your fifteen ATS-optimized picks.
        
OUTPUT
Return one string in this exact format (competence1, competence2, ..., Competence15) and nothing else:
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
You are a professional ATS resume expert. Your inputs are:
  1. A text file containing one of my project or internship experiences described exhaustively.
  2. A job description for the role I’m applying to.


             
Please generate concise bullet points that:
  - Clearly explain what I did and achieved during each experience.
  - Incorporate exact keywords and phrases from the job description where they apply.
  - List experiences in reverse-chronological order (most recent first).
  - Adhere to ATS-friendly formatting:
      • Plain, single-column layout without headers, footers, tables, borders, shading, or graphics  
      • Spell out abbreviations on first use (e.g., “Metric Tons (MT)”)  
      • Use strong action verbs to start each bullet  
      • Quantify results wherever possible (e.g., “increased throughput by 30 %”)  
      • Tailor the wording to mirror the job description’s requirements  
  - Use the STAR method (Situation, Task, Action, Result) to structure each bullet point.
  - If very few technical words are matched try to include one or two MAX from the description and adapt them to my experience IF THEY MAKE TECHNICAL SENSE.  
STRICT RULES:
    - return exactly {number} bullet points. Not more, not less.
    - Maximum 1 line per bullet point.    
    - Use the job description to identify the most relevant skills and experiences to highlight.
    - Avoid using the same wording as the job description; instead, rephrase it in your own words.
    - Do not include any personal information, such as your name, address, or contact details.
    - Output only the final bullet points preceeded by "-*" each.
Here’s an example input:
             
<PROJECT/INTERNSHIP>
{internship}
</COURSE/SKILL LIST>
             
<JOB DESCRIPTION>
{job_description}
</JOB DESCRIPTION>
         
---

Now, please process that input and output your five ATS-optimized picks.
        
OUTPUT
Return one JSON object for this schema and nothing else:
{format_instructions}
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions(),
                  number=number)

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)

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


def run_summary_agent(job_description):
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
  - Incorporate quantifiable achievements once.
  - Use active language and strong action verbs (e.g., led, developed, implemented).  
  - Avoid generic phrases and clichés; focus on specific strengths and accomplishments.  

             
- **ATS Optimization:** Ensure the summary is ATS-friendly by including relevant keywords from the job description.
STRICT RULE : I AM AN INDUSTRIAL/AI and SOFTWARE ENGINEER, DO NOT MENTION ANYTHING ELSE.
STRICT RULE 2: MEntion that im searching for a full-time position (CDI or CDD) in the summary.
### Output Format ###

Provide the professional summary as a standalone paragraph, ready to be placed at the top of a CV.
             
---        
OUTPUT
Return one JSON object for this schema and nothing else:
{format_instructions}
'''),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.4)

    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=[]
    )

    filename= "personalaspirations.txt"
    filename2= "Latexoriginalexample.txt"

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
    1. A text file containing one of my project or internship experiences described exhaustively.
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
- From the projects list, select exactly **three** that best match.
- Use the job description to identify the most relevant projects to highlight, in order of relevance.
- For each selected project, use the **verbatim** title and description, but wrap **at least one** high-impact tool/action/result word in LaTeX \textbf  for emphasis.
- **Do not** change any other wording or formatting.
- **DO NOT** use any special characters or commands (like \downarrow,\times...) Stick with normal stuff.
- **CRUCIAL** If you make something up in the technicalities of a certain project, make sure it makes perfect sense technically.
- Try to include the technologies used in the project description. (not necessarily all of them, but at least two).
- Output **three** `\item` entries, **exactly** like this:

         
\item \textbf ProjectTitle1 \newline
ProjectTitle1 description with \textbf emphasized  keyword(s).
         
\item \textbf ProjectTitle2  \newline
ProjectTitle2 description with \textbf emphasized  keyword(s).
         
\item \textbf ProjectTitle3  \newline
ProjectTitle3 description with \textbf emphasized  keyword(s).
         
Projects list:
{projects}

Job description:
{job_description}

RETURN exactly one JSON object matching this schema (and nothing else):
{format_instructions}
"""),
        ("placeholder", "{agent_scratchpad}")
    ]).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)
    agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=[])
    executor = AgentExecutor(agent=agent, tools=[], verbose=True)

    with open(filename, "r", encoding="utf-8") as file:
        projects = file.read()

    raw = executor.invoke({
        "projects": projects,
        "job_description": job_description,
        "agent_scratchpad": ""
    })
    output = json.loads(raw["output"])
    return output["latex_block"]

if __name__ == "__main__":



    load_dotenv()


    latex_file= "Latexoriginalexample.txt"
    job_description= input('job description: ')

    ##Cours notables:

    # exclude_list = ""

    # for i in range(3):
    #     matieres = parse_first_line_column(i+1)
    #     output= run_courses_agent(job_description, matieres, exclude_list)
    #     current= output
    #     current= escape_latex_special_chars(current)
    #     replace_placeholder_in_file_inplace(latex_file, i+1, current)
    #     exclude_list += output + ", "
    
    
    # ###Internships:
    # for i in range(4):
    #     if i==0:
    #         filename= "Experience_Dassault.txt"
    #         j=3
    #     elif i==1:
    #         filename= "Experience_Aimovement.txt"
    #         j=3
    #     elif i==2:
    #         filename= "Experience_TNC.txt"
    #         j=2
    #     elif i==3:
    #         filename= "Experience_Lear.txt"
    #         j=2
        
    #     current=transform_bullets(run_internship_agent(job_description, filename, j))


    #     current= wrapper_agent(current, job_description)
    #     current= escape_latex_special_chars(current)

    #     replace_placeholder_in_file_inplace(latex_file, i+4, current)
    #     print("Experience " + str(i+1) + " done")
    #     print(current)

    # ## ###Projects:
    # filename= "projects.txt"
    # current= projects_agent( filename, job_description)
    # current= escape_latex_special_chars(current)
    # print(current)
    # replace_placeholder_in_file_inplace(latex_file, 8, current)

    # print("Projects done")

    exclud= ""


    print(run_skills_agent(job_description, "latexoriginalexample.txt", exclud))

    print(run_summary_agent(job_description))

