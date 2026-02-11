from fastapi import APIRouter, HTTPException, status

from api.auth.auth_service import AuthServiceDependency
from api.message.label.label_create_service import LabelCreateRequest, LabelCreateServiceDependency
from api.message.label.label_delete_service import LabelDeleteServiceDependency
from api.service_errors import ForbiddenError, NotFoundError, ResourceAssocationError
from api.thread.models.flat_message import FlatMessage

label_router = APIRouter(prefix="/label")


@label_router.put("/")
async def create_label(
    message_id: str,
    request: LabelCreateRequest,
    label_create_service: LabelCreateServiceDependency,
    auth_service: AuthServiceDependency,
) -> FlatMessage:
    token = auth_service.optional_auth()
    try:
        return await label_create_service.create(message_id=message_id, request=request, user_id=token.client)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=repr(e)) from e


@label_router.delete("/{label_id}")
async def delete_label(
    message_id: str,
    label_id: str,
    label_delete_service: LabelDeleteServiceDependency,
    auth_service: AuthServiceDependency,
) -> None:
    token = auth_service.optional_auth()
    try:
        return await label_delete_service.delete_one(message_id=message_id, label_id=label_id, user_id=token.client)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=repr(e)) from e
    except ResourceAssocationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=repr(e)) from e
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=repr(e)) from e
