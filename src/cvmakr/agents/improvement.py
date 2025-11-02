"""Agents responsible for refining a resume based on ATS feedback."""

from __future__ import annotations

import json
from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class RefinementResponse(BaseModel):
    revised_resume: str
    applied_changes: List[str]
    integrated_keywords: List[str]


def refine_resume_with_feedback(
    job_description: str,
    resume_latex: str,
    missing_keywords: List[str],
    authenticity_concerns: List[str],
    language: str = "fr",
) -> RefinementResponse:
    """Return an updated LaTeX resume that addresses compliance feedback."""

    parser = PydanticOutputParser(pydantic_object=RefinementResponse)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an expert resume editor specialising in ATS optimisation.

Inputs:
<JOB_DESCRIPTION>{job_description}</JOB_DESCRIPTION>

<CURRENT_RESUME_LATEX>
{resume_latex}
</CURRENT_RESUME_LATEX>

Missing keywords to address (maximum 10% new additions allowed) (And do not dump them on the summary section):
{missing_keywords}

Authenticity concerns flagged by reviewers:
{authenticity_concerns}

Target language: {target_language}

Requirements:
- Keep every statement truthful; only add details that are strongly implied by the current resume.
- Integrate missing keywords only where technically coherent with existing responsibilities, or create new bullet points if absolutely necessary.
- Preserve THE EXACT LaTeX structure and commands; do not introduce new placeholders AT ANY COST AT ALL (The most crucial thing).
- Keep tone professional and human, no generic filler.
- Rewrite or adapt every section so the final resume is fully written in {target_language} (Do not touch on the structure of the file ONLY translate words and sentences). If it is already in that language, keep the content natural.
- If no adjustments are necessary, return the original resume unchanged but explain why in applied_changes.
- Make sure you miss some keywords in the summary so that it looks more human-written and more authentic and less AI-generated.
Return JSON only:
{format_instructions}
""",
            ),
        ]
    ).partial(
        format_instructions=parser.get_format_instructions(),
        job_description=job_description,
        resume_latex=resume_latex,
        missing_keywords=json.dumps(missing_keywords, ensure_ascii=False),
        authenticity_concerns=json.dumps(authenticity_concerns, ensure_ascii=False),
        target_language="French" if language.lower().startswith("fr") else "English",
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    chain = prompt | llm | parser
    return chain.invoke({})
