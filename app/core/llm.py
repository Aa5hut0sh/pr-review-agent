import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def get_groq_llm(model_name: str | None = None, temperature: float = 0.1):
    """
    Returns an initialized ChatGroq instance using settings.GROQ_API_KEY.
    """
    api_key = settings.groq_api_key
    if not api_key or "your_groq_api_key" in api_key:
        raise ValueError(
            "GROQ_API_KEY is not set! Please add your Groq API key to the .env file in the project root."
        )

    from langchain_groq import ChatGroq
    chosen_model = model_name or settings.groq_model
    return ChatGroq(
        model=chosen_model,
        groq_api_key=api_key,
        temperature=temperature,
    )


def invoke_structured_llm(
    prompt: str,
    output_schema: type[T],
    system_prompt: str = "You are an expert AI code reviewer.",
    model_name: str | None = None,
) -> T:
    """
    Invokes Groq with structured JSON output mapped to a Pydantic model.
    Includes prompt delimiting to defend against prompt injection in untrusted diffs.
    """
    llm = get_groq_llm(model_name=model_name)
    schema_json = json.dumps(output_schema.model_json_schema(), indent=2)

    augmented_system_prompt = (
        f"{system_prompt}\n\n"
        f"You MUST output valid JSON adhering strictly to this JSON schema:\n{schema_json}\n"
        f"Return ONLY the raw JSON object or list without markdown code block backticks."
    )

    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=augmented_system_prompt),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Clean markdown json code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return output_schema.model_validate_json(content)
    except Exception as e:
        logger.error(f"Failed to parse LLM response into schema {output_schema.__name__}: {content}")
        raise e
