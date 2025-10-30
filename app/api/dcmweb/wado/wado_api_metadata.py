"""
This module contains handlers for wado paths for dicom metadata.
WADO metadata queries are parsed and then passed to the configured data service.

"""
from typing import List
import json
from xml.etree import ElementTree
from fastapi import APIRouter, Request, Depends, Response, HTTPException  # noqa
from app.utils.dicom_media import DicomMediaMultipartMessage, \
                                DicomMediaPartXML, DicomMediaType  # noqa
from app.utils.accept_headers import parse_accept_headers, parse_accept_charset_query, AcceptHeaders

from app.utils.xml_json_converters import json_to_xml
from app.schema.dicom_instance import DCMInstance
from app.utils.openapi_metadata import standard_response
wado_metadata_router = APIRouter()

def inst_combine_metadata(inst: DCMInstance) -> str:
    """
    Combines the metadata of a DICOM instance with additional pixel data information.

    Args:
        inst (DCMInstance): The DICOM instance object containing the metadata and pixel data.

    Returns:
        str: The combined metadata as a JSON string.
    """

    if inst.pixel_data:
        temp = json.loads(inst.meta_data)
        temp["00280002"] = {"vr":"US", "Value":[inst.pixel_data.samples_per_pixel]} # samples per pixel
        temp["00280004"] = {"vr":"CS", "Value":[inst.pixel_data.photometric_interpretation]}
        temp["00280010"] = {"vr":"US", "Value":[inst.pixel_data.rows]}
        temp["00280011"] = {"vr":"US", "Value":[inst.pixel_data.columns]}
        temp["00280100"] = {"vr":"US", "Value":[inst.pixel_data.bits_allocated]}
        temp["00280101"] = {"vr":"US", "Value":[inst.pixel_data.bits_stored]}
        temp["00280102"] = {"vr":"US", "Value":[inst.pixel_data.high_bit]}
        temp["00280103"] = {"vr":"US", "Value":[inst.pixel_data.pixel_representation]}
        temp["00280106"] = {"vr":"US", "Value":[inst.pixel_data.planar_configuration]}
        #if inst.pixel_data.smallest_image_pixel_value:
        #    temp[""] = {"vr":"", "Value":[]}
        #if inst.pixel_data.largest_image_pixel_value:
        #    temp[""] = {"vr":"", "Value":[]}

        if inst.pixel_data.photometric_interpretation == " PALETTE COLOR":
            temp["00281101"] = {"vr":"US", "Value":inst.pixel_data.red_palette_color_lookup_table_data}
            temp["00281102"] = {"vr":"US", "Value":inst.pixel_data.blue_palette_color_lookup_table_data}
            temp["00281103"] = {"vr":"US", "Value":inst.pixel_data.green_palette_color_lookup_table_data}

            temp["00281201"] = {"vr":"OW", "Value":[inst.pixel_data.red_palette_color_lookup_table_data]}
            temp["00281202"] = {"vr":"OW", "Value":[inst.pixel_data.blue_palette_color_lookup_table_data]}
            temp["00281203"] = {"vr":"OW", "Value":[inst.pixel_data.green_palette_color_lookup_table_data]}

        return json.dumps(temp)

    return inst.meta_data

def select_media_type_metadata(accept_query : AcceptHeaders, accept_headers : AcceptHeaders) ->  DicomMediaType:
    """
    Selects the appropriate DICOM media type based on the provided accept headers and accept query parameters.

    The selection process follows these steps:
    1. Identify the target's Resource Category
    2. Select the representation with the highest priority supported media type for
    that category in the Accept Query Parameter.
    3. If no media type in the Accept Query Parameter is supported, select the
    highest priority supported media type for that category in the Accept header field, if any.
    4. Otherwise, select the default media type for the category, if the Accept header field
    contains a wildcard media range matching the category, if any.
    5. Otherwise, return a 406 (Not Acceptable).

    For instance types, this is not really important as it will only be DICOM.
    However, the Transfer syntax will be determined by this selection.

    Args:
        accept_query (AcceptHeaders): The accept headers from the query parameters.
        accept_headers (AcceptHeaders): The accept headers from the request.

    Returns:
        DicomMediaType: The selected DICOM media type.
    """


    # 1. Identify the target's Resource Category
    # 2. Select the representation with the highest priority supported media type for that category in
    # the Accept Query Parameter.
    # 3. If no media type in the Accept Query Parameter is supported,
    # select the highest priority supported media type for that category in the Accept header field, if any.
    # 4. Otherwise, select the default media type for the category,
    # if the Accept header field contains a wildcard media range matching the category, if any.
    # 5. Otherwise, return a 406 (Not Acceptable).
    # for instance types, this is not really important as will only be DICOM.
    # But Transfer syntax will be determined by this!


    sorted_accept_query = sorted(accept_query.accept_types,key=lambda x: x.quality,reverse=True) ## currently only


    for accept_type in sorted_accept_query:
        #
        if accept_type.type == DicomMediaType.DICOM_XML or accept_type.type == DicomMediaType.DICOM_JSON:
            return accept_type.type
        if accept_type.type == DicomMediaType.ANY:
            return DicomMediaType.DICOM_XML


    sorted_accept_params = sorted(accept_headers.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_params:
        if accept_type.type == DicomMediaType.DICOM_XML or accept_type.type == DicomMediaType.DICOM_JSON:
            return accept_type.type
        if accept_type.type == DicomMediaType.ANY:
            return DicomMediaType.DICOM_XML

    return DicomMediaType.DICOM_XML

def accept_headers_metadata(request: Request) -> AcceptHeaders:
    """
    Extracts the accept headers from the request and validates that they contain a supported DICOM media type.

    Args:
        request (Request): The incoming request.

    Returns:
        AcceptHeaders: The parsed and validated accept headers.

    Raises:
        HTTPException: If the accept header is missing or does not contain a supported DICOM media type.
    """


    if request.headers.get("accept", None) is None:
        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)
    accept_header_types = [x.type for x in accept_headers.accept_types]

    if DicomMediaType.ANY not in accept_header_types \
       and DicomMediaType.DICOM_JSON not in accept_header_types \
       and DicomMediaType.DICOM_XML not in accept_header_types:

        raise HTTPException(status_code=406,
                            detail="Invalid media type in accept header")

    return accept_headers


def package_response_metadata_json(insts: List[DCMInstance]) -> Response:
    """
    Packages the response metadata as a JSON document.

    Args:
        insts (List[DCMInstance]): A list of DCMInstance objects containing the metadata to be packaged.

    Returns:
        Response: A FastAPI Response object containing the packaged metadata as a JSON document.
    """

    temp = "["
    count = 0
    for inst in insts:
        temp = temp + inst_combine_metadata(inst)
        count = count + 1
        if count != len(insts):
            temp = temp + ' , '
    temp = temp+' ]'

    media_type = 'application/dicom+json'
    response = Response(content=temp, media_type=media_type)
    return response


def package_response_metadata_xml(insts: List[DCMInstance]) -> Response:
    """
    Packages the response metadata as a DICOM XML document.

    Args:
        insts (List[DCMInstance]): A list of DCMInstance objects containing the metadata to be packaged.

    Returns:
        Response: A FastAPI Response object containing the packaged metadata as a DICOM XML document.
    """

    multipart_msg = DicomMediaMultipartMessage()

    for inst in insts:
        # parse the inst and convert to xml
        xml_ele = json_to_xml(json.loads(inst.meta_data))
        xml_str = ElementTree.tostring(xml_ele, encoding='utf8')
        part = DicomMediaPartXML(xml_str)
        multipart_msg.parts.append(part)

    cont_bytes = multipart_msg.to_bytes()
    media_type = f'multipart/related; boundary={multipart_msg.boundary}; type="application/dicom+xml"'  # noqa
    response = Response(content=cont_bytes, media_type=media_type)
    return response



@wado_metadata_router.get("/studies/{study_uid}/metadata", tags=["wado", "study", "metadata"],
                          responses={**standard_response})  # noqa
async def get_study_metadata_api(study_uid: str,
                                 request: Request,
                                 accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
                                 accept_headers: AcceptHeaders = Depends(accept_headers_metadata)) -> Response:  # noqa
    """
    Retrieves the metadata for a study identified by the provided `study_uid`.

    Args:
        study_uid (str): The unique identifier for the study.
        request (Request): The incoming HTTP request object.
        accept_query (AcceptHeaders): The parsed `Accept` headers from the query string.
        accept_headers (AcceptHeaders): The parsed `Accept` headers from the request headers.

    Returns:
        Response: A FastAPI Response object containing the packaged metadata in the requested format (JSON or XML).
    """
    # will get the study and is multi-part binary or bulk data
    # need to check the headers
    insts = await request.state.data_service.get_study(study_uid)

    media_type=select_media_type_metadata(accept_query,accept_headers)

    if media_type is DicomMediaType.DICOM_XML:
        return package_response_metadata_xml(insts)
    return package_response_metadata_json(insts)



@wado_metadata_router.get("/studies/{study_uid}/series/{series_uid}/metadata",
                 tags=["wado", "series", "metadata"],
                          responses={**standard_response})
async def get_series_metadata_api(study_uid: str,
                                  series_uid: str,
                                  request: Request,
                                  accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
                                  accept_headers: AcceptHeaders = Depends(accept_headers_metadata))-> Response:  # noqa
    # will get the series metadata

    """
    Retrieves the metadata for a series identified by the provided `study_uid` and `series_uid`.

    Args:
        study_uid (str): The unique identifier for the study.
        series_uid (str): The unique identifier for the series.
        request (Request): The incoming HTTP request object.
        accept_query (AcceptHeaders): The parsed `Accept` headers from the query string.
        accept_headers (AcceptHeaders): The parsed `Accept` headers from the request headers.

    Returns:
        Response: A FastAPI Response object containing the packaged metadata in the requested format (JSON or XML).
    """
    insts = await request.state.data_service.get_series(study_uid,
                                                            series_uid)

    media_type=select_media_type_metadata(accept_query,accept_headers)
    if media_type is DicomMediaType.DICOM_XML:
        return package_response_metadata_xml(insts)
    return package_response_metadata_json(insts)



@wado_metadata_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/metadata",  # noqa
                 tags=["wado", "instance", "metadata"],
                          responses={**standard_response})
async def get_instance_metadata_api(study_uid: str,
                                    series_uid: str,
                                    instance_uid: str,
                                    request: Request,
                                    accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                                    accept_headers: AcceptHeaders = Depends(accept_headers_metadata)) -> Response:
    """
    Retrieves the metadata for an instance identified by the provided `study_uid`, `series_uid`, and `instance_uid`.

    Args:
        study_uid (str): The unique identifier for the study.
        series_uid (str): The unique identifier for the series.
        instance_uid (str): The unique identifier for the instance.
        request (Request): The incoming HTTP request object.
        accept_query (AcceptHeaders): The parsed `Accept` headers from the query string.
        accept_headers (str): The parsed `Accept` headers from the request headers.

    Returns:
        Response: A FastAPI Response object containing the packaged metadata in the requested format (JSON or XML).
    """
    # will get the study
    # instance = data_service.get_instance(study_uid,series_uid,instance_uid)
    insts = [await request.state.data_service.get_instance(study_uid,
                                                               series_uid,
                                                               instance_uid)]
    media_type=select_media_type_metadata(accept_query,accept_headers)
    if media_type is DicomMediaType.DICOM_XML:
        return package_response_metadata_xml(insts)
    return package_response_metadata_json(insts)
