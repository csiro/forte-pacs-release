'''
This module contains handlers for wado paths related to bulkdata only.
WADO bulkdata queries are parsed and then passed to the configured data service.

'''
from typing import List
import logging
from pydicom.uid import ExplicitVRLittleEndian
from fastapi import APIRouter, Request, Depends, Response, HTTPException  # noqa
from app.utils.dicom_media import DicomMediaMultipartMessage, DicomMediaPartDICOMImage, \
    DicomMediaPartBytes, DicomMediaType, transfer_syntax_to_media_type_images  # noqa
from app.utils.dicom_storage_sop_class import  is_supported_transfer_syntax  # noqa
from app.utils.accept_headers import parse_accept_headers, parse_accept_charset_query, AcceptHeaders
from app.schema.dicom_instance import DCMInstance
from app.utils.transcode import convert_dcm
from app.codecs.codec_registry import CodecRegistry
from app.utils.openapi_metadata import bd_resp

wado_bulkdata_router = APIRouter()

logger = logging.getLogger(__name__)

#
#  Below routes are for PART 10 Binary images only. Asking for bulk data using legacy will
#  return a reroute to the bulkdata api
#
#

def select_media_type_and_transfer_syntax_pixel(sop_class_uid : str,
    accept_query : AcceptHeaders, accept_headers : AcceptHeaders) -> str :
    """
        Selects the appropriate media type and transfer syntax for the pixel data of a
        DICOM instance based on the client's Accept headers and query parameters.

        Args:
            sop_class_uid (str): The SOP class UID of the DICOM instance.
            accept_headers (AcceptHeaders): The Accept headers from the client request.
            accept_query (AcceptQuery): The Accept query parameters from the client request.

        Returns:
            str: The selected transfer syntax for the pixel data.
    """

    # 1. Identify the target's Resource Category
    # 2. Select the representation with the highest priority supported media type for that category in the
    #   Accept Query Parameter.
    # 3. If no media type in the Accept Query Parameter is supported, select the highest priority supported
    #   media type for that category in the Accept header field, if any.
    # 4. Otherwise, select the default media type for the category, if the Accept header field contains a
    #   wildcard media range matching the category, if any.
    # 5. Otherwise, return a 406 (Not Acceptable).
    # for instance types, this is not really important as will only be DICOM. But Transfer syntax will be
    #   determined by this!


    sorted_accept_query = sorted(accept_query.accept_types,key=lambda x: x.quality,reverse=True) ## currently only


    transfer_syntax : str = ""
    for accept_type in sorted_accept_query:
        #
        if accept_type.type == DicomMediaType.DICOM or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax is not  None:
                ## is this an acceptable transfer_syntax for this sopclass
                if is_supported_transfer_syntax(sop_class_uid,accept_type.transfer_syntax):
                    transfer_syntax= accept_type.transfer_syntax
            else:
                transfer_syntax = ExplicitVRLittleEndian # default transfer syntax


    if transfer_syntax:
        return transfer_syntax

    sorted_accept_params = sorted(accept_headers.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_params:
        #
        if accept_type.type == DicomMediaType.DICOM or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax is not None:
                if is_supported_transfer_syntax(sop_class_uid,accept_type.transfer_syntax):
                    transfer_syntax= accept_type.transfer_syntax
                transfer_syntax= accept_type.transfer_syntax
            else:
                transfer_syntax = ExplicitVRLittleEndian # default transfer syntax

    return transfer_syntax


# this is bulk data so we will be sending back either a single part
# or multipart images
def package_pixel_data(inst : DCMInstance, accept_headers : AcceptHeaders,
                       accept_query : AcceptHeaders, server_base_url : str,
                       codec_registry : CodecRegistry) -> List[DicomMediaPartDICOMImage]:
    """
    Packages the pixel data frames for a DICOM instance into a list of DICOM media parts.

    Args:
        inst (DCMInstance): The DICOM instance containing the pixel data.
        accept_headers (AcceptHeaders): The Accept headers from the client request.
        accept_query (AcceptQuery): The Accept query parameters from the client request.
        server_base_url (str): The base URL of the server.

    Returns:
        List[DicomMediaPartDICOMImage]: A list of DICOM media parts containing the pixel data frames.
    """



    requested_transfer_syntax = select_media_type_and_transfer_syntax_pixel(inst.sop_class_uid,\
        accept_headers,accept_query)

    pixel_data = []
    if inst.pixel_data:
        pixel_data = inst.pixel_data.frames
        if inst.pixel_data.transfer_syntax_uid != requested_transfer_syntax:
            inst = convert_dcm(inst,requested_transfer_syntax,codec_registry)
    # if default


    parts = []
    frame_number = 1
    for frame in pixel_data:

        headers={}
        ## content-location headers
        headers["content-location"]=server_base_url+\
            f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/frames/{frame_number}"
        part = DicomMediaPartDICOMImage(frame, \
            transfer_syntax_to_media_type_images(requested_transfer_syntax),requested_transfer_syntax,headers)
        frame_number += 1
        parts.append(part)

    return parts

# this is bulk data so we will be sending back either a single part
# or multipart images
def package_pixel_data_frame(inst : DCMInstance ,accept_headers : AcceptHeaders,
                                accept_query : AcceptHeaders, include_frame : int ,
                                server_base_url : str , codec_registry : CodecRegistry) \
                                    -> List[DicomMediaPartDICOMImage]:
    """
    Packages the pixel data frame for a DICOM instance into a DICOM media part.

    Args:
        inst (DCMInstance): The DICOM instance containing the pixel data.
        accept_headers (AcceptHeaders): The Accept headers from the client request.
        accept_query (AcceptQuery): The Accept query parameters from the client request.
        include_frame (int): The index of the frame to include (1-based).
        server_base_url (str): The base URL of the server.

    Returns:
        List[DicomMediaPartDICOMImage]: A list containing a single DICOM media
        part with the pixel data for the requested frame.
    """


    requested_transfer_syntax = select_media_type_and_transfer_syntax_pixel(inst.sop_class_uid,\
        accept_headers,accept_query)


    if inst.pixel_data is not None:
       # if inst.pixel_data.transfer_syntax_uid != requested_transfer_syntax:
       #     inst = convert_dcm(inst,requested_transfer_syntax, codec_registry)

        pixel_data = inst.pixel_data# if default

        if pixel_data is not None:
            parts = []

            headers={}
            ## content-location headers
            headers["Content-Location"]=server_base_url+\
            f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/frames/{include_frame}"

            if pixel_data.frames is not None and  include_frame <= len(pixel_data.frames)-1:
                if inst.pixel_data.transfer_syntax_uid is not None:
                    parts=[DicomMediaPartDICOMImage(pixel_data.frames[include_frame-1],\
                                transfer_syntax_to_media_type_images(inst.pixel_data.transfer_syntax_uid ),\
                                inst.pixel_data.transfer_syntax_uid ,headers=headers)]
            return parts

    return []


def package_response_bd(insts: List[DCMInstance], accept_headers : AcceptHeaders,
                        accept_query : AcceptHeaders, server_base_url : str, codec_registry : CodecRegistry)->Response:
    """
        Packages the DICOM bulk data  for a list of DICOM instances into a DICOM media multipart response.

        Args:
            insts (List[DCMInstance]): The list of DICOM instances to package.
            accept_headers (AcceptHeaders): The Accept headers from the client request.
            accept_query (AcceptHeaders): The Accept query parameters from the client request.
            server_base_url (str): The base URL of the server.

        Returns:
            Response: A DICOM media multipart response containing the bulk data and pixel data
            for the requested DICOM instances.
    """

    if not has_media_type_exp_vrle_other_bulkdata(accept_query,\
                    accept_headers):
        raise HTTPException(status_code=406, detail="Not Acceptable")

    multipart_msg = DicomMediaMultipartMessage()

    for inst in insts:

        if inst.other_bulk_data:
            if len(inst.other_bulk_data.keys()) != 0 : ## will need to check for cases there are no bulk data items

                for (bdt,bd) in inst.other_bulk_data.items():
                    headers={}
                    ## content-location headers
                    headers["content-location"]=server_base_url+\
                    f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/bulkdata/{bdt}"
                    part = DicomMediaPartBytes(bd,headers)
                    multipart_msg.parts.append(part)

            # wrap teh pixel data
                multipart_msg.parts.extend(package_pixel_data(inst,accept_headers,\
                                                              accept_query,server_base_url, codec_registry))

    cc = multipart_msg.to_bytes()
    media_type = f'multipart/related; boundary={multipart_msg.boundary}; '
    response = Response(content=cc, media_type=media_type)
    return response


def package_response_pixel_frame(inst : DCMInstance, accept_headers : AcceptHeaders,
    accept_query : AcceptHeaders, frames : List[int], server_base_url : str, codec_registry: CodecRegistry)->Response:
    """
        Packages the DICOM pixel data for a list of DICOM instances into a DICOM media multipart response,
        with each frame of the pixel data in a separate part.

        Args:
            inst (DCMInstance): The DICOM instance to package.
            accept_headers (AcceptHeaders): The Accept headers from the client request.
            accept_query (AcceptHeaders): The Accept query parameters from the client request.
            frames (List[int]): The list of frame indices to include in the response.
            server_base_url (str): The base URL of the server.

        Returns:
            Response: A DICOM media multipart response containing the pixel data for the requested frames.
    """

    multipart_msg = DicomMediaMultipartMessage()

    for frame in frames:
        # wrap teh pixel data
        multipart_msg.parts.extend(package_pixel_data_frame(inst,accept_headers,accept_query,\
                                                            frame,server_base_url, codec_registry))

    cc = multipart_msg.to_bytes()
    media_type = f'multipart/related; type="application/octet-stream; \
        transfer-syntax=1.2.840.10008.1.2.1"; boundary={multipart_msg.boundary};'
    response = Response(content=cc, media_type=media_type)
    return response

def package_response_pixel(insts: List[DCMInstance], accept_headers : AcceptHeaders,
    accept_query : AcceptHeaders, server_base_url : str, codec_registry : CodecRegistry)->Response:
    """
    Packages the DICOM pixel data for a list of DICOM instances into a DICOM media multipart response.

    Args:
        insts (List[DCMInstance]): The list of DICOM instances to package.
        accept_headers (AcceptHeaders): The Accept headers from the client request.
        accept_query (AcceptHeaders): The Accept query parameters from the client request.
        server_base_url (str): The base URL of the server.

    Returns:
        Response: A DICOM media multipart response containing the pixel data for the requested instances.
    """

    multipart_msg = DicomMediaMultipartMessage()

    for inst in insts:
        # wrap teh pixel data
        multipart_msg.parts.extend(package_pixel_data(inst,accept_headers,accept_query,server_base_url, codec_registry))

    cc = multipart_msg.to_bytes()
    media_type = f'multipart/related; boundary={multipart_msg.boundary}; '
    response = Response(content=cc, media_type=media_type)
    return response

def package_response_bd_tag(insts: List[DCMInstance], accept_headers : AcceptHeaders,
    accept_query : AcceptHeaders,  tag : str, server_base_url : str)->Response:
    """
    Packages the DICOM bulk data for a list of DICOM instances into a DICOM media multipart response.

    Args:
        insts (List[DCMInstance]): The list of DICOM instances to package.
        accept_headers (AcceptHeaders): The Accept headers from the client request.
        accept_query (AcceptHeaders): The Accept query parameters from the client request.
        tag (str): The tag of the bulk data to include in the response.
        server_base_url (str): The base URL of the server.

    Returns:
        Response: A DICOM media multipart response containing the bulk data for the requested instances and tag.
    """

    if not has_media_type_exp_vrle_other_bulkdata(accept_query,\
                    accept_headers):
        raise HTTPException(status_code=406, detail="Not Acceptable")

    multipart_msg = DicomMediaMultipartMessage()

    for inst in insts:

        if inst.other_bulk_data and len(inst.other_bulk_data.keys()) != 0:

            for (bd_tag,bd) in inst.other_bulk_data.items():
                if bd_tag != tag:
                    continue
                headers={}
                ## content-location headers
                headers["content-location"]=server_base_url+\
                f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/bulkdata/{bd_tag}"
                part = DicomMediaPartBytes(bd,headers)
                multipart_msg.parts.append(part)


    cc = multipart_msg.to_bytes()
    media_type = f'multipart/related; boundary={multipart_msg.boundary}; type="application/octet-stream"'
    response = Response(content=cc, media_type=media_type)
    return response


def accept_headers_bulkdata(request: Request) -> AcceptHeaders:
    """
    Parses the Accept headers from the incoming request and returns an AcceptHeaders object.

    Args:
        request (Request): The incoming request object.

    Returns:
        AcceptHeaders: An object representing the parsed Accept headers.

    Raises:
        HTTPException: If the Accept header is not present in the request.
    """


    if request.headers.get("accept",None) is None:
        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)

    return accept_headers

def has_media_type_exp_vrle_other_bulkdata(accept_query : AcceptHeaders, accept_headers : AcceptHeaders)-> bool:
    """
    Determines if the provided accept headers and query parameters have a valid media type and
    transfer syntax for DICOM bulk data.

    Args:
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        bool: True if the accept headers and query parameters have a valid media type and transfer syntax,
            False otherwise.
    """



    # 1. Identify the target's Resource Category
    # 2. Select the representation with the highest priority supported media type for that
    # category in the Accept Query Parameter.
    # 3. If no media type in the Accept Query Parameter is supported, select the highest priority
    # supported media type for that category in the Accept header field, if any.
    # 4. Otherwise, select the default media type for the category, if the Accept header field contains
    # a wildcard media range matching the category, if any.
    # 5. Otherwise, return a 406 (Not Acceptable).
    # for instance types, this is not really important as will only be DICOM.
    # But Transfer syntax will be determined by this!


    sorted_accept_query = sorted(accept_query.accept_types,key=lambda x: x.quality,reverse=True) ## currently only


    for accept_type in sorted_accept_query:
        #
        if accept_type.type == DicomMediaType.BYTES or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax is not None:
                if accept_type.transfer_syntax == ExplicitVRLittleEndian:
                    return True

            else:
                return True

    sorted_accept_params = sorted(accept_headers.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_params:
        #
        if accept_type.type == DicomMediaType.BYTES or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax is not None:
                if accept_type.transfer_syntax == ExplicitVRLittleEndian:
                    return True

            else:
                return True

        raise HTTPException(status_code=406,
                            detail="Invalid media type in accept header")

    return False


####
##
##  Below routes are for bulkdata only
##
####
# Bulkdata in a multipart response shall have a Content-Location header field that corresponds to the URI
# contained in the corresponding Element in the Metadata.
## returna octet string

## octet string for everything except pixel data
## for pixel data, we will have to have potentially convert to a
## representation that is asked for

@wado_bulkdata_router.get("/studies/{study_uid}/bulkdata/",tags=["wado","study","bulkdata"],
                          responses= {**bd_resp})
async def get_bulkdata_study_api(study_uid: str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) ->  Response:
    """
        Retrieves the bulkdata for a given study.

        Args:
            study_uid (str): The unique identifier for the study.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the bulkdata for the requested study.
        """
        # will get the study

    # if no octstream or any headers present, then we have to


    insts = await request.state.data_service.get_study(study_uid)


    return package_response_bd(insts,accept_headers,accept_query,\
                               request.state.server_base_url, request.state.codec_registry)


@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/bulkdata/",tags=["wado","series","bulkdata"],
                          responses= {**bd_resp})
async def get_bulkdata_series_api(study_uid: str, series_uid: str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    # will get the study
    """
    Retrieves the bulkdata for a given series.

    Args:
        study_uid (str): The unique identifier for the study.
        series_uid (str): The unique identifier for the series.
        request (Request): The incoming HTTP request.
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        A response containing the bulkdata for the requested series.
    """

    insts = await request.state.data_service.get_series(study_uid,series_uid)

    return package_response_bd(insts,accept_headers,accept_query,\
                               request.state.server_base_url, request.state.codec_registry)


@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/bulkdata/",
    tags=["wado","instance","bulkdata"],
    responses= {**bd_resp})
async def get_bulkdata_instance_api(study_uid:str, series_uid:str, instance_uid:str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
        Retrieves the bulkdata for a given instance.

        Args:
            study_uid (str): The unique identifier for the study.
            series_uid (str): The unique identifier for the series.
            instance_uid (str): The unique identifier for the instance.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the bulkdata for the requested instance.
        """
        # will get the study

    inst = await request.state.data_service.get_instance(study_uid,series_uid,instance_uid)

    return package_response_bd([inst],accept_headers,accept_query,\
                               request.state.server_base_url, request.state.codec_registry)

@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/bulkdata/{tag}",
    tags=["wado","instance","bulkdata","single"],
    responses= {**bd_resp})
async def get_bulkdata_api(study_uid:str, series_uid:str, instance_uid:str, tag:str,request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
        Retrieves the bulkdata for a given instance and DICOM tag.

        Args:
            study_uid (str): The unique identifier for the study.
            series_uid (str): The unique identifier for the series.
            instance_uid (str): The unique identifier for the instance.
            tag (str): The DICOM tag to retrieve the bulkdata for.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the bulkdata for the requested instance and DICOM tag.
    """
        # will get the study

    insts = await request.state.data_service.get_instance(study_uid,series_uid,instance_uid)

    return package_response_bd_tag(insts,accept_headers,accept_query,tag,request.state.server_base_url)



## just get the pixel data
@wado_bulkdata_router.get("/studies/{study_uid}/pixeldata/",tags=["wado","study","bulkdata"],
                          responses= {**bd_resp})
async def get_pixeldata_study_api(study_uid: str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
        Retrieves the pixel data for a given study.

        Args:
            study_uid (str): The unique identifier for the study.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the pixel data for the requested study.
    """
        # will get the study

    # if no octstream or any headers present, then we have to

    insts = await request.state.data_service.get_study(study_uid)

    return package_response_pixel(insts,accept_headers,accept_query,\
                                  request.state.server_base_url,request.state.codec_registry)


@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/pixeldata/",tags=["wado","series","bulkdata"],
                          responses= {**bd_resp})

async def get_pixeldata_series_api(study_uid: str, series_uid: str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
            Retrieves the pixel data for a given series.

            Args:
                study_uid (str): The unique identifier for the study.
                series_uid (str): The unique identifier for the series.
                request (Request): The incoming HTTP request.
                accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
                accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

            Returns:
                A response containing the pixel data for the requested series.
    """
        # will get the study

    insts = await request.state.data_service.get_series(study_uid,series_uid)

    return package_response_pixel(insts,accept_headers,accept_query,\
                                  request.state.server_base_url,request.state.codec_registry)


@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/pixeldata/",
    tags=["wado","instance","bulkdata"],
    responses= {**bd_resp})
async def get_pixeldata_instance_api(study_uid:str, series_uid:str, instance_uid:str, request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
        Retrieves the pixel data for a given instance.

        Args:
            study_uid (str): The unique identifier for the study.
            series_uid (str): The unique identifier for the series.
            instance_uid (str): The unique identifier for the instance.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the pixel data for the requested instance.
    """
        # will get the study



    inst = await request.state.data_service.get_instance(study_uid,series_uid, instance_uid)

    return package_response_pixel([inst],accept_headers,accept_query,\
                                  request.state.server_base_url,request.state.codec_registry)

@wado_bulkdata_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frame}",
    tags=["wado","instance","bulkdata"],
    responses= {**bd_resp})
async def get_framedata_instance_api(study_uid:str, series_uid:str, instance_uid:str, frame: str,request: Request,
    accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
    accept_headers : AcceptHeaders = Depends(accept_headers_bulkdata)) -> Response:
    """
        Retrieves the pixel data for the specified frames of a given instance.

        Args:
            study_uid (str): The unique identifier for the study.
            series_uid (str): The unique identifier for the series.
            instance_uid (str): The unique identifier for the instance.
            frame (str): A comma-separated list of frame numbers to retrieve.
            request (Request): The incoming HTTP request.
            accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
            accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

        Returns:
            A response containing the pixel data for the requested frames of the instance.
    """
        # will get the study

    frames = [int(x) for x in frame.split(',')]
    inst = await request.state.data_service.get_instance(study_uid,series_uid, instance_uid)
    return package_response_pixel_frame(inst,accept_headers,accept_query,frames, \
                                        request.state.server_base_url,request.state.codec_registry)
