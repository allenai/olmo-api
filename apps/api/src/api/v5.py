from fastapi import APIRouter

v5_router = APIRouter(prefix="/v5")


@v5_router.get("/hello")
def hello_world() -> str:
    return "Hello world"
