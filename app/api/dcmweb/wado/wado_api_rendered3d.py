"""
This module contains handlers for wado paths for rendered thumbnail.
WADO rendered thumbnail queries are parsed and then passed to the configured data service.


"""
from typing import  Annotated
from fastapi import APIRouter, Request, Depends, Response, Query
from app.utils.accept_headers import parse_accept_charset_query, AcceptHeaders
from app.utils.openapi_metadata import ni_resp
from app.utils.rendered_query import Window, Viewport, ThreeVec, Orientation, RenderingMethod, \
    get_query_viewport, get_query_window, accept_headers_rendered, get_query_3vec


wado_rendered3d_router = APIRouter()

#The Acceptable Media Types shall be either DICOM media-types or Rendered media types, but not both.
# If the Acceptable Media Types contains both DICOM and Rendered Media Types, the origin server
# shall return 400 (Bad Request).





@wado_rendered3d_router.get("/studies/{study_uid}/rendered3d",tags=["wado","study"],
                                    responses={**ni_resp})
async def get_study_rendered3d_api(study_uid: str, request: Request,
                                 volumeinputreference : str | None,
                                 match: str | None,
                                 renderingmethod : RenderingMethod | None = None,
                                 orientation: Orientation | None =None,
                                 viewpointposition : ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 viewpointlookat: ThreeVec | None = Depends(get_query_3vec, use_cache=False),
                                 viewpointup: ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 mprslab : float | None = None,
                                 swivelrange : float | None = None,
                                 volumetriccurvepoint : float | None = None,
                                 animationstepsize : float | None = None,
                                 animationrate : float | None = None,
                                 renderedvolumetricmetadata : Annotated[str|None, Query(regex="yes")]=None,
                                 annotation: str | None = None,
                                 quality: int | None = None,
                                 iccprofile: str | None = None,
                                 viewport: Viewport | None = Depends(get_query_viewport),
                                 window: Window | None = Depends(get_query_window),
                                 accept_query: AcceptHeaders = Depends(parse_accept_charset_query),
                                 accept_headers: AcceptHeaders = Depends(accept_headers_rendered)) -> Response:
    # pylint: disable=unused-argument
    """Get rendered representation of a study.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        request (Request): HTTP request object
        volumeinputreference (str | None): See https://www.dicomstandard.org/News-dir/ftsup/docs/sups/sup228.pdf
        match (str | None):
        renderingmethod (RenderingMethod | None) :
        orientation (Orientation | None) :
        viewpointposition (ThreeVec | None) :
        viewpointlookat (ThreeVec | None) :
        viewpointup (ThreeVec | None) :
        mprslab (float | None) :
        swivelrange (float | None) :
        volumetriccurvepoint (float | None) :
        animationstepsize (float | None) :
        animationrate (float | None) :
        renderedvolumetricmetadata (str | None) :
        annotation (str | None): Optional annotation text
        quality (int | None): Optional image quality parameter
        iccprofile (str | None): Optional ICC profile specification
        viewport (Viewport | None): Optional viewport parameters
        window (Window | None): Optional windowing parameters
        accept_query (AcceptHeaders): Accept headers from query parameters
        accept_headers (AcceptHeaders): Accept headers from HTTP headers

    Returns:
        Response: HTTP response with 501 Not Implemented status
    """
    # pylint: disable=unused-argument

    return Response(status_code=501)


@wado_rendered3d_router.get("/studies/{study_uid}/series/{series_uid}/rendered3d",tags=["wado","series"],
                                    responses={**ni_resp})
async def get_series_rendered3d_api(study_uid:str, series_uid:str, request: Request,
                                 volumeinputreference : str | None,
                                 match: str | None,
                                 renderingmethod : RenderingMethod | None = None,
                                 orientation: Orientation | None =None,
                                 viewpointposition : ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 viewpointlookat: ThreeVec | None = Depends(get_query_3vec, use_cache=False),
                                 viewpointup: ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 mprslab : float | None = None,
                                 swivelrange : float | None = None,
                                 volumetriccurvepoint : float | None = None,
                                 animationstepsize : float | None = None,
                                 animationrate : float | None = None,
                                 renderedvolumetricmetadata : Annotated[str|None, Query(regex="yes")]=None,
                                 annotation: str | None = None, quality: int | None = None,
                                 iccprofile : str | None = None,
                                 viewport: Viewport | None  = Depends(get_query_viewport),
                                 window: Window | None = Depends(get_query_window),
                                 accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                 accept_headers : AcceptHeaders= Depends(accept_headers_rendered))->Response:
    # pylint: disable=unused-argument

    """Get rendered representation of a series.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        series_uid (str): Series instance UID
        request (Request): HTTP request object
        volumeinputreference (str | None): See https://www.dicomstandard.org/News-dir/ftsup/docs/sups/sup228.pdf
        match (str | None):
        renderingmethod (RenderingMethod | None) :
        orientation (Orientation | None) :
        viewpointposition (ThreeVec | None) :
        viewpointlookat (ThreeVec | None) :
        viewpointup (ThreeVec | None) :
        mprslab (float | None) :
        swivelrange (float | None) :
        volumetriccurvepoint (float | None) :
        animationstepsize (float | None) :
        animationrate (float | None) :
        renderedvolumetricmetadata (str | None) :
        annotation (str | None): Optional annotation text
        quality (int | None): Optional image quality parameter
        iccprofile (str | None): Optional ICC profile specification
        viewport (Viewport | None): Optional viewport parameters
        window (Window | None): Optional windowing parameters
        accept_query (AcceptHeaders): Accept headers from query parameters
        accept_headers (AcceptHeaders): Accept headers from HTTP headers

    Returns:
        Response: HTTP response with 501 Not Implemented status
    """
    # pylint: disable=unused-argument

    return Response(status_code=501)



@wado_rendered3d_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/rendered3d",
                                tags=["wado","instance"],
                                responses={**ni_resp})
async def get_instance_rendered3d_api(study_uid:str, series_uid:str, instance_uid:str, request: Request,
                                 volumeinputreference : str | None,
                                 match: str | None,
                                 renderingmethod : RenderingMethod | None = None,
                                 orientation: Orientation | None =None,
                                 viewpointposition : ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 viewpointlookat: ThreeVec | None = Depends(get_query_3vec, use_cache=False),
                                 viewpointup: ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 mprslab : float | None = None,
                                 swivelrange : float | None = None,
                                 volumetriccurvepoint : float | None = None,
                                 animationstepsize : float | None = None,
                                 animationrate : float | None = None,
                                 renderedvolumetricmetadata : Annotated[str|None, Query(regex="yes")]=None,
                                 annotation: str | None = None, quality: int | None = None,
                                 iccprofile : str | None = None,
                                 viewport: Viewport  | None = Depends(get_query_viewport),
                                 window: Window  | None = Depends(get_query_window),
                                 accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                 accept_headers : AcceptHeaders= Depends(accept_headers_rendered))-> Response:
    # pylint: disable=unused-argument

    """Get rendered representation of a instance.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        series_uid (str): Series instance UID
        instance_uid (str): Instance instance UID
        request (Request): HTTP request object
        volumeinputreference (str | None): See https://www.dicomstandard.org/News-dir/ftsup/docs/sups/sup228.pdf
        match (str | None):
        renderingmethod (RenderingMethod | None) :
        orientation (Orientation | None) :
        viewpointposition (ThreeVec | None) :
        viewpointlookat (ThreeVec | None) :
        viewpointup (ThreeVec | None) :
        mprslab (float | None) :
        swivelrange (float | None) :
        volumetriccurvepoint (float | None) :
        animationstepsize (float | None) :
        animationrate (float | None) :
        renderedvolumetricmetadata (str | None) :
        annotation (str | None): Optional annotation text
        quality (int | None): Optional image quality parameter
        iccprofile (str | None): Optional ICC profile specification
        viewport (Viewport | None): Optional viewport parameters
        window (Window | None): Optional windowing parameters
        accept_query (AcceptHeaders): Accept headers from query parameters
        accept_headers (AcceptHeaders): Accept headers from HTTP headers

    Returns:
        Response: HTTP response with a rendered image
    """
    return Response(status_code=501)


@wado_rendered3d_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frames}/rendered3d", # pylint: disable=line-too-long
                                tags=["wado","instance"],
                                responses={**ni_resp})
async def get_frame_rendered3d_api(study_uid:str, series_uid:str, instance_uid:str,
                                 frames:str ,request: Request,
                                 volumeinputreference : str | None,
                                 match: str | None,
                                 renderingmethod : RenderingMethod | None= None,
                                 orientation: Orientation | None =None,
                                 viewpointposition : ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 viewpointlookat: ThreeVec | None = Depends(get_query_3vec, use_cache=False),
                                 viewpointup: ThreeVec | None = Depends(get_query_3vec, use_cache=False) ,
                                 mprslab : float | None = None,
                                 swivelrange : float | None = None,
                                 volumetriccurvepoint : float | None = None,
                                 animationstepsize : float | None = None,
                                 animationrate : float | None = None,
                                 renderedvolumetricmetadata : Annotated[str|None, Query(regex="yes")]=None,
                                 annotation: str | None = None,
                                 quality: int | None = None,
                                 iccprofile : str | None = None,
                                 viewport: Viewport  | None = Depends(get_query_viewport),
                                 window: Window  | None = Depends(get_query_window),
                                 accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                 accept_headers : AcceptHeaders = Depends(accept_headers_rendered)) \
                                            -> Response:
    """Get rendered representation of a frame rendered thumbnail.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        series_uid (str): Series instance UID
        instance_uid (str): Instance instance UID
        frames (str): Frame number(s)
        request (Request): HTTP request object
        volumeinputreference (str | None): See https://www.dicomstandard.org/News-dir/ftsup/docs/sups/sup228.pdf
        match (str | None):
        renderingmethod (RenderingMethod | None) :
        orientation (Orientation | None) :
        viewpointposition (ThreeVec | None) :
        viewpointlookat (ThreeVec | None) :
        viewpointup (ThreeVec | None) :
        mprslab (float | None) :
        swivelrange (float | None) :
        volumetriccurvepoint (float | None) :
        animationstepsize (float | None) :
        animationrate (float | None) :
        renderedvolumetricmetadata (str | None) :
        annotation (str | None): Optional annotation text
        quality (int | None): Optional image quality parameter
        iccprofile (str | None): Optional ICC profile specification
        viewport (Viewport | None): Optional viewport parameters
        window (Window | None): Optional windowing parameters
        accept_query (AcceptHeaders): Accept headers from query parameters
        accept_headers (AcceptHeaders): Accept headers from HTTP headers

    Returns:
        Response: HTTP response with 501 Not Implemented status
    """
    # pylint: disable=unused-argument

    return Response(status_code=501)
