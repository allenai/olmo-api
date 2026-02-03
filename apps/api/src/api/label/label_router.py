from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api.auth.auth_service import AuthServiceDependency
from api.label.label_create_service import LabelCreateRequest, LabelCreateServiceDependency
from api.label.label_delete_service import LabelDeleteServiceDependency
from api.service_errors import ForbiddenError, NotFoundError, ResourceExistsError
from core.label.label import Label

label_router = APIRouter(prefix="/labels")


@label_router.post("/")
async def create_label(
    request: LabelCreateRequest, label_create_service: LabelCreateServiceDependency, auth_service: AuthServiceDependency
) -> Label:
    token = auth_service.optional_auth()
    try:
        return await label_create_service.create(request=request, user_id=token.client)
    except NotFoundError as e:
        # create returns NotFound for the message, so it becomes a 422
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=repr(e)) from e
    except ResourceExistsError as e:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail=repr(e)) from e


@label_router.delete("/{label_id}")
async def delete_label(
    label_id: str, label_delete_service: LabelDeleteServiceDependency, auth_service: AuthServiceDependency
) -> Label:
    token = auth_service.optional_auth()
    try:
        return await label_delete_service.delete_one(label_id=label_id, user_id=token.client)
    except NotFoundError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=repr(e)) from e
    except ForbiddenError as e:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=repr(e)) from e
