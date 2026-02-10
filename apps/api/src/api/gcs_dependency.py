from typing import Annotated

from fastapi import Depends

from core.google_cloud_storage import GoogleCloudStorage


# This is needed because fastapi DI follows into the __init__ method of GCS (which has optional session param)
# we can provide a function to intialize it for fastapi
def get_google_cloud_storage() -> GoogleCloudStorage:
    return GoogleCloudStorage()


# GCS is defined in core, which doesn't have fastapi -- move this if/when its used elsewhere
GoogleCloudStorageDependency = Annotated[GoogleCloudStorage, Depends(get_google_cloud_storage)]
