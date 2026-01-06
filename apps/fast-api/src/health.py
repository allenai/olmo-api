from fastapi import APIRouter, status

health_router = APIRouter(prefix="/health")


# Standard k8 health check route
@health_router.get("/", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def health() -> None:
    return
