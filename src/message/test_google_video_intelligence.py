from google.cloud import videointelligence

from .GoogleVideoIntelligence import GoogleVideoIntelligenceResponse


def test_result_is_false_if_frame_is_tagged():
    response = videointelligence.AnnotateVideoResponse()

    # Create video annotation results with explicit content
    video_result = videointelligence.VideoAnnotationResults()

    # Create explicit annotation with frames
    explicit_annotation = videointelligence.ExplicitContentAnnotation()

    # Create a frame with explicit content detected
    frame = videointelligence.ExplicitContentFrame()
    frame.pornography_likelihood = videointelligence.Likelihood.VERY_LIKELY

    # Add frame to explicit annotation
    explicit_annotation.frames.append(frame)

    # Add explicit annotation to video results
    video_result.explicit_annotation = explicit_annotation

    # Add video results to response
    response.annotation_results.append(video_result)

    result = GoogleVideoIntelligenceResponse(response)

    assert result.is_safe() is False


def test_result_is_true_():
    response = videointelligence.AnnotateVideoResponse()

    # Create video annotation results with explicit content
    video_result = videointelligence.VideoAnnotationResults()

    # Create explicit annotation with frames
    explicit_annotation = videointelligence.ExplicitContentAnnotation()

    # Create a frame with explicit content detected
    frame = videointelligence.ExplicitContentFrame()
    frame.pornography_likelihood = videointelligence.Likelihood.UNLIKELY

    # Add frame to explicit annotation
    explicit_annotation.frames.append(frame)

    # Add explicit annotation to video results
    video_result.explicit_annotation = explicit_annotation

    # Add video results to response
    response.annotation_results.append(video_result)

    result = GoogleVideoIntelligenceResponse(response)

    assert result.is_safe() is True
