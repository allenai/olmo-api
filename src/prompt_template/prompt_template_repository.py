from sqlalchemy.orm import Session

from src.dao.engine_models.prompt_template import PromptTemplate


def get_prompt_templates(session: Session) -> list[PromptTemplate]:
    return session.query(PromptTemplate).where(PromptTemplate.deleted == None).all()  # noqa: E711
