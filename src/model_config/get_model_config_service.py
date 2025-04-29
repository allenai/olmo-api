from pydantic import ByteSize
from sqlalchemy import select
from sqlalchemy.orm import Session, selectin_polymorphic, sessionmaker

from src.config.Model import Model, MultiModalModel
from src.config.ModelConfig import FileRequiredToPromptOption
from src.dao.engine_models.model_config import ModelConfig as DAOModelConfig
from src.dao.engine_models.model_config import MultiModalModelConfig as DAOMultiModalModelConfig


def get_model_config(session_maker: sessionmaker[Session]) -> list[Model]:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(DAOModelConfig, [DAOModelConfig, DAOMultiModalModelConfig])

        stmt = select(DAOModelConfig).options(polymorphic_loader_opt)

        stmt = stmt.filter_by(internal=False)
        stmt.order_by(DAOModelConfig.order.asc())
        results = session.scalars(stmt).all()

        processed_results = []
        for m in results:
            item = Model(
                id=m.id,
                name=m.name,
                host=m.host,
                description=m.description,
                compute_source_id=m.model_id_on_host,
                model_type=m.model_type,
                system_prompt=m.default_system_prompt,
                family_id=m.family_id,
                family_name=m.family_name,
                available_time=None,
                deprecation_time=None,
            )
            if isinstance(m, DAOMultiModalModelConfig):
                item = MultiModalModel(
                    id=m.id,
                    name=m.name,
                    host=m.host,
                    description=m.description,
                    compute_source_id=m.model_id_on_host,
                    model_type=m.model_type,
                    system_prompt=m.default_system_prompt,
                    family_id=m.family_id,
                    family_name=m.family_name,
                    available_time=None,
                    deprecation_time=None,
                    accepted_file_types=m.accepted_file_types,
                    max_files_per_message=m.max_files_per_message,
                    require_file_to_prompt=m.require_file_to_prompt or FileRequiredToPromptOption.NoRequirement,
                    max_total_file_size=ByteSize(m.max_total_file_size) if m.max_total_file_size is not None else None,
                    allow_files_in_followups=m.allow_files_in_followups or False,
                )

            processed_results.append(item)

        return processed_results


def get_model_config_admin(session_maker: sessionmaker[Session]) -> list[Model]:
    with session_maker.begin() as session:
        polymorphic_loader_opt = selectin_polymorphic(DAOModelConfig, [DAOModelConfig, DAOMultiModalModelConfig])

        stmt = select(DAOModelConfig).options(polymorphic_loader_opt)
        stmt.order_by(DAOModelConfig.order.asc())
        results = session.scalars(stmt).all()

        processed_results = []
        for m in results:
            item = Model(
                id=m.id,
                name=m.name,
                host=m.host,
                description=m.description,
                compute_source_id=m.model_id_on_host,
                model_type=m.model_type,
                system_prompt=m.default_system_prompt,
                family_id=m.family_id,
                family_name=m.family_name,
                available_time=m.available_time,
                deprecation_time=m.deprecation_time,
            )
            if isinstance(m, DAOMultiModalModelConfig):
                item = MultiModalModel(
                    id=m.id,
                    name=m.name,
                    host=m.host,
                    description=m.description,
                    compute_source_id=m.model_id_on_host,
                    model_type=m.model_type,
                    system_prompt=m.default_system_prompt,
                    family_id=m.family_id,
                    family_name=m.family_name,
                    available_time=m.available_time,
                    deprecation_time=m.deprecation_time,
                    accepted_file_types=m.accepted_file_types,
                    max_files_per_message=m.max_files_per_message,
                    require_file_to_prompt=m.require_file_to_prompt or FileRequiredToPromptOption.NoRequirement,
                    max_total_file_size=ByteSize(m.max_total_file_size) if m.max_total_file_size is not None else None,
                    allow_files_in_followups=m.allow_files_in_followups or False,
                )

            processed_results.append(item)

        return processed_results
