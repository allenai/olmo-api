from enum import StrEnum


class Permissions(StrEnum):
    READ_INTERNAL_MODELS = "read:internal-models"
    WRITE_MODEL_CONFIG = "write:model-config"
    WRITE_BYPASS_SAFETY_CHECKS = "write:bypass-safety-check"
