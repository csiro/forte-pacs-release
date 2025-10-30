"""
This module contains handlers for wado paths for rendered thumbnail.
WADO rendered thumbnail queries are parsed and then passed to the configured data service.


"""
import io
from fastapi import APIRouter, Request, Depends, Response, HTTPException
from PIL import  ImageCms
from app.utils.accept_headers import  parse_accept_charset_query, AcceptHeaders
from app.utils.dicom_storage_sop_class import is_renderable_image_sop_class
from app.utils.rendered_query import Window, Viewport, get_query_viewport, get_query_window, accept_headers_rendered
from app.utils.openapi_metadata import ni_resp, rend_resp
from app.utils.rendered_utils import select_media_type_rendered, render_image

wado_rendered_router = APIRouter()

#The Acceptable Media Types shall be either DICOM media-types or Rendered media types, but not both.
# If the Acceptable Media Types contains both DICOM and Rendered Media Types, the origin server
# shall return 400 (Bad Request).







@wado_rendered_router.get("/studies/{study_uid}/rendered",tags=["wado","study"],
                                    responses={**ni_resp})
async def get_study_rendered_api(study_uid: str, request: Request,
                                 annotation: str | None = None,
                                 quality: int | None = None,
                                 iccprofile: str | None = None,
                                 viewport: Viewport | None = Depends(get_query_viewport),
                                 window: Window | None = Depends(get_query_window),
                                 accept_query: AcceptHeaders = Depends(parse_accept_charset_query),
                                 accept_headers: AcceptHeaders = Depends(accept_headers_rendered)) -> Response:
    """Get rendered representation of a study.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        request (Request): HTTP request object
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


@wado_rendered_router.get("/studies/{study_uid}/series/{series_uid}/rendered",tags=["wado","series"],
                                    responses={**ni_resp})
async def get_series_rendered_api(study_uid:str, series_uid:str, request: Request,
                                 annotation: str | None = None, quality: int | None = None,
                                 iccprofile : str | None = None,
                                 viewport: Viewport | None  = Depends(get_query_viewport),
                                 window: Window | None = Depends(get_query_window),
                                 accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                 accept_headers : AcceptHeaders= Depends(accept_headers_rendered))->Response:
    """Get rendered representation of a series.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        series_uid (str): Series instance UID
        request (Request): HTTP request object
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



@wado_rendered_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/rendered",
                            tags=["wado","instance"],
                            responses={**rend_resp})
async def get_instance_rendered_api(study_uid:str, series_uid:str, instance_uid:str, request: Request,
                                    annotation: str | None = None, quality: int | None = None,
                                    iccprofile : str | None = None,
                                    viewport: Viewport  | None = Depends(get_query_viewport),
                                    window: Window  | None = Depends(get_query_window),
                                    accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                    accept_headers : AcceptHeaders= Depends(accept_headers_rendered))-> Response:

    """Get rendered representation of a instance.

    Returns a rendered image representation of an entire study. Currently not implemented.

    Args:
        study_uid (str): Study instance UID
        series_uid (str): Series instance UID
        instance_uid (str): Instance instance UID
        request (Request): HTTP request object
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
    if quality and quality < 1 and quality > 100:
        raise HTTPException(status_code=400,
                detail="Quality parameter should be between 1 and 100")

    inst = await request.state.data_service.get_instance(study_uid,series_uid,instance_uid)

    # is this a renderable image
    if not is_renderable_image_sop_class(inst.sop_class_uid):
        return Response(status_code=501)

    if inst.pixel_data is None:
        return Response(status_code=501)

    if inst.pixel_data.frames is None:
        return Response(status_code=501)

    selected_media_type = select_media_type_rendered(inst.sop_class_uid, inst.pixel_data.number_of_frames, \
                                                     accept_query, accept_headers)
    # is this a multiframe image
    if selected_media_type == "image/gif":
        if iccprofile is not None and iccprofile != "no":
            raise HTTPException(status_code=400,
                detail="GIF rendered media type for multiframe data does not support an icc profile")

    pil_icc_profile = None
    ## get the icc color profile stuff
    if iccprofile:
        if iccprofile in ["yes","srgb"]:
            pil_icc_profile = ImageCms.createProfile("sRGB")
        elif iccprofile == "adobergb":

            pil_icc_profile = ImageCms.createProfile(request.state.icc_directory.joinpath("AdobeCompat-v2.icc"))

        elif iccprofile == "rommrgb":
            pil_icc_profile = ImageCms.createProfile(request.state.icc_directory.joinpath("ISO22028-2_ROMM-RGB.icc"))

        elif iccprofile == "displayp3":
            pil_icc_profile = ImageCms.createProfile(request.state.icc_directory.joinpath("Display_P3.icc"))

    all_pil_images = []
    #
    if selected_media_type == "image/gif":

        for ii in range(0,inst.pixel_data.number_of_frames):
            ri = render_image(inst,ii,viewport,window,annotation,request.state.codec_registry)
            if ri is not None:
                all_pil_images.append(ri)
    else:
        ri = render_image(inst,inst.pixel_data.number_of_frames/2,viewport,
                                           window,annotation,request.state.codec_registry)
        if ri is not None:
            all_pil_images.append(ri)

    ## write to bytes io.
    with io.BytesIO() as buffer:

        if len(all_pil_images) >= 1:

            if selected_media_type == "image/gif":
                # combine multiple together
                if len(all_pil_images) > 1:
                    all_pil_images[0].save(buffer,format="GIF",save_all=True,append_images=all_pil_images[1:],\
                        optimize=False,duration=250,loop=0)
                else:
                    all_pil_images[0].save(buffer,format="GIF",optimize=False)
            elif selected_media_type == "image/png":
                ## can have
                if pil_icc_profile:
                    all_pil_images[0].save(buffer,format="PNG",icc_profile=pil_icc_profile)
                else:
                    all_pil_images[0].save(buffer,format="PNG")
            elif selected_media_type == "image/jpeg":
                jpeg_quality=95
                if quality:
                    jpeg_quality *= int(float(quality)/100.0)

                if pil_icc_profile:
                    all_pil_images[0].save(buffer,format="JPEG",icc_profile=pil_icc_profile, quality=jpeg_quality)
                else:
                    all_pil_images[0].save(buffer,format="JPEG",quality=jpeg_quality)
            elif selected_media_type == "image/jp2":
                all_pil_images[0].save(buffer,format="JPEG 2000")

            buffer.seek(0)
            return Response(content=buffer.read(), media_type=selected_media_type)
        else:
            return Response(status_code=501)

@wado_rendered_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frames}/rendered", # pylint: disable=line-too-long
                                    tags=["wado","instance"],
                                    responses={**ni_resp})
async def get_frame_rendered_api(study_uid:str, series_uid:str, instance_uid:str,
                                           frames:str ,request: Request,
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
