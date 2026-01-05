from db.models.prompt_template import PromptTemplate
from src.dao.flask_sqlalchemy_session import current_session


def get_prompt_templates() -> list[PromptTemplate]:
    return current_session.query(PromptTemplate).where(PromptTemplate.deleted == None).all()  # noqa: E711
