from fastapi import APIRouter

from api.message.label.label_router import label_router

message_router = APIRouter(prefix="/message")

# add label prefixed under the message_id
message_router.include_router(label_router, prefix="/{message_id}")
