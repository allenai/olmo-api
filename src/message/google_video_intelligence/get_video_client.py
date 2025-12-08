from functools import cache

from google.cloud import videointelligence


@cache
def get_video_intelligence_client():
    return videointelligence.VideoIntelligenceServiceClient()
