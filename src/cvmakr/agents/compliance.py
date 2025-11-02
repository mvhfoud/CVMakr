"""Agents focused on ATS compliance and authenticity checks."""

from __future__ import annotations

from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class KeywordItem(BaseModel):
    keyword: str


class KeywordResponse(BaseModel):
    must_have: List[KeywordItem]


def extract_mandatory_keywords(job_description: str) -> list[str]:
    """Return a concise list of must-mention keywords pulled from the JD."""

    parser = PydanticOutputParser(pydantic_object=KeywordResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are an expert ATS auditor.

Goal: read the job description and list the 8 to 12 *must have* hard-skill keywords that recruiters expect to see mirrored in a resume.

Guidelines:
- Prioritise technical tools, platforms, methodologies, or certifications.
- Skip soft skills, company names, years of experience, and generic verbs.
- Choose terms that are meaningful for keyword scanners.
- Ensure each keyword is a single noun phrase (no commas or slashes).

Return only the JSON specified.

{format_instructions}
""",
            ),
            ("human", "{job_description}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    chain = prompt | llm | parser
    result = chain.invoke({"job_description": job_description})
    return [item.keyword for item in result.must_have]


class AuthenticityResponse(BaseModel):
    human_score: float
    reassuring_message: str
    risks: List[str]


def coherence_review(job_description: str, resume_text: str) -> AuthenticityResponse:
    """Check the resume tone for authenticity and over-tailoring issues."""

    parser = PydanticOutputParser(pydantic_object=AuthenticityResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a senior recruiter evaluating whether a resume summary + content feels human, truthful, and not auto-generated.

Inputs:
<JD>{job_description}</JD>
<RESUME>{resume_text}</RESUME>

Instructions:
- human_score: float 0.0-1.0 (0 synthetic, 1 authentic). Stay objective.
- reassuring_message: one concise sentence if everything looks good.
- risks: list suspicious points (hallucinations, exaggerations, tailoring red flags). Return [] if none.

Focus on realism and consistency with JD without forcing repetitions.

Return JSON only.
{format_instructions}
""",
            ),
        ]
    ).partial(
        format_instructions=parser.get_format_instructions(),
        job_description=job_description,
        resume_text=resume_text,
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    chain = prompt | llm | parser
    return chain.invoke({})
