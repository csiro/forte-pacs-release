"""
This module contains handlers for wado paths for dicom instance data (PS3.10).
WADO  queries are parsed and then passed to the configured data service.

"""
import json
from typing import List, Dict
import logging
import pydicom
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian,DeflatedExplicitVRLittleEndian,\
                        ExplicitVRBigEndian
from fastapi import APIRouter, Request, Depends, Response, HTTPException , status # noqa
from app.utils.dicom_media import DicomMediaMultipartMessage, DicomMediaPartDICOM, DicomMediaType  # noqa
from app.utils.dicom_storage_sop_class import  is_compressed_transfer_syntax, is_supported_transfer_syntax  # noqa
from app.utils.accept_headers import parse_accept_headers, parse_accept_charset_query, AcceptHeaders
from app.schema.dicom_instance import DCMInstance
from app.utils.transcode import convert_dcm
from app.codecs.codec_registry import CodecRegistry
from app.utils.openapi_metadata import inst_resp


#
# This comment block is for TODO and bits of info form the spec
# that may or may not yest be incorporated into code.
#
# If the Acceptable Media Types contains both DICOM and Rendered Media Types,
# the origin server shall return 400 (Bad Request).
# The response to a request without an Accept header field shall be 406 (Not Acceptable)
#

logger = logging.getLogger(__name__)

wado_instance_router = APIRouter()

def inst_combine_metadata(inst: DCMInstance) -> Dict[str, Dict]:
    """
    Combines the metadata and pixel metadat from a DCMInstance object into a dictionary.

    Args:
        inst (DCMInstance): The DCMInstance object containing the metadata to be combined.

    Returns:
        Dict[str, Dict]: A dictionary containing the combined metadata.
    """

    temp = json.loads(inst.meta_data)

    pixel_data = inst.pixel_data

    if pixel_data:
        temp["00280002"] = {"vr":"US", "Value":[pixel_data.samples_per_pixel]} # samples per pixel
        temp["00280004"] = {"vr":"CS", "Value":[pixel_data.photometric_interpretation]}
        temp["00280010"] = {"vr":"US", "Value":[pixel_data.rows]}
        temp["00280011"] = {"vr":"US", "Value":[pixel_data.columns]}
        temp["00280100"] = {"vr":"US", "Value":[pixel_data.bits_allocated]}
        temp["00280101"] = {"vr":"US", "Value":[pixel_data.bits_stored]}
        temp["00280102"] = {"vr":"US", "Value":[pixel_data.high_bit]}
        temp["00280103"] = {"vr":"US", "Value":[pixel_data.pixel_representation]}
        temp["00280106"] = {"vr":"US", "Value":[pixel_data.planar_configuration]}

        if pixel_data.photometric_interpretation == " PALETTE COLOR":
            temp["00281101"] = {"vr":"US", "Value":pixel_data.red_palette_color_lookup_table_data}
            temp["00281102"] = {"vr":"US", "Value":pixel_data.blue_palette_color_lookup_table_data}
            temp["00281103"] = {"vr":"US", "Value":pixel_data.green_palette_color_lookup_table_data}

            temp["00281201"] = {"vr":"OW", "Value":[pixel_data.red_palette_color_lookup_table_data]}
            temp["00281202"] = {"vr":"OW", "Value":[pixel_data.blue_palette_color_lookup_table_data]}
            temp["00281203"] = {"vr":"OW", "Value":[pixel_data.green_palette_color_lookup_table_data]}

        if not is_compressed_transfer_syntax(pixel_data.transfer_syntax_uid):
            if "7FE00010" in temp.keys() and pixel_data.bits_allocated == 16:
                temp["7FE00010"]["vr"] = "OW"
    return temp

def inst_to_dcm(inst: DCMInstance, server_base_url:str) -> pydicom.FileDataset:
    """
        Converts a DCMInstance object to a pydicom.Dataset object, handling compressed and multi-frame pixel data.

        Args:
            inst (DCMInstance): The DCMInstance object to be converted.
            server_base_url (str): The base URL of the server hosting the DICOM data.

        Returns:
            pydicom.Dataset: The converted pydicom.Dataset object.
    """

    pixel_data_uri =  server_base_url+\
        f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/pixel_data"

    bulk_data = inst.other_bulk_data
    if not bulk_data:
        bulk_data={}
    if inst.pixel_data:
        # if this is multi-frame or compressed
        if is_compressed_transfer_syntax(inst.pixel_data.transfer_syntax_uid):
            bulk_data[pixel_data_uri]  = pydicom.encaps.encapsulate(inst.pixel_data.frames) # all frames
        else:
            bulk_data[pixel_data_uri]  = b''.join(inst.pixel_data.frames)

    def bulk_data_converter(bd_uri: str) -> bytes:

        if bd_uri in bulk_data:
            return bulk_data[bd_uri]
        return b""

    ## need to merge the
    temp = inst_combine_metadata(inst)
    dcm = pydicom.Dataset.from_json(temp, bulk_data_converter)


    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.UID(inst.sop_class_uid)
    if inst.pixel_data:
        if inst.pixel_data.transfer_syntax_uid and \
            pydicom.uid.UID(inst.pixel_data.transfer_syntax_uid) not in \
                [ImplicitVRLittleEndian,DeflatedExplicitVRLittleEndian,ExplicitVRBigEndian] :
            file_meta.TransferSyntaxUID = pydicom.uid.UID(inst.pixel_data.transfer_syntax_uid)
        else:
            file_meta.TransferSyntaxUID =pydicom.uid.ExplicitVRLittleEndian
    else:
        file_meta.TransferSyntaxUID =pydicom.uid.ExplicitVRLittleEndian


    ## if there isn't a specific character set, then set it to UTF-8
    if dcm.get("SpecificCharacterSet",None) is None:
        dcm.SpecificCharacterSet = "ISO_IR 192"

    ## This might not work
    ds = pydicom.FileDataset(None, dcm, file_meta=file_meta, is_implicit_VR=False, is_little_endian=True) # type: ignore

    return ds


def package_response_ps310(insts: List[DCMInstance], accept_headers : AcceptHeaders,
                           accept_query : AcceptHeaders, server_base_url : str,
                           codec_registry : CodecRegistry)->Response:
    """
    Packages the response for a DICOM WADO-RS request using the PS3.10 binary format.

    Args:
        insts (List[DCMInstance]): A list of DICOM instances to include in the response.
        accept_headers (AcceptHeaders): The accept headers from the request.
        accept_query (AcceptHeaders): The accept headers from the query parameters.
        server_base_url (str): The base URL of the server.

    Returns:
        Response: A multipart DICOM response in the PS3.10 binary format.
    """
    multipart_msg = DicomMediaMultipartMessage()

    for inst in insts:

        requested_transfer_syntax = select_media_type_and_transfer_syntax_instance(inst.sop_class_uid,\
                                                                                   accept_headers,accept_query)

        # compress the dicom here
        inst_new = inst
        if inst.pixel_data:
            if requested_transfer_syntax and \
                inst.pixel_data.transfer_syntax_uid != requested_transfer_syntax:

                inst_new = convert_dcm(inst,requested_transfer_syntax, codec_registry)
        # if default
        dcm = inst_to_dcm(inst_new, server_base_url)

        headers = {}
        headers["Content-Location"]=server_base_url+\
            f"/studies/{inst.study_uid}/series/{inst.series_uid}/instances/{inst.instance_uid}/frames/1"


        part = DicomMediaPartDICOM(dcm,headers=headers)
        multipart_msg.parts.append(part)

    cc = multipart_msg.to_bytes()
    media_type = f'multipart/related; boundary={multipart_msg.boundary}; type="application/dicom"'
    response = Response(content=cc, media_type=media_type)
    return response


def accept_headers_instance_frame(request: Request) -> AcceptHeaders:
    """
    Validates the accept headers in the request and returns the parsed accept headers.

    Args:
        request (Request): The incoming request.

    Raises:
        HTTPException: If the accept header is not present or contains an invalid media type.

    Returns:
        AcceptHeaders: The parsed accept headers.
    """



    if request.headers.get("accept",None) is None:
        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)
    accept_header_types = [x.type for x in accept_headers.accept_types]


    if DicomMediaType.ANY not in accept_header_types \
       and DicomMediaType.BYTES not in accept_header_types:

        raise HTTPException(status_code=406,
                            detail="Invalid media type in accept header")

    if DicomMediaType.DICOM_IMAGE in accept_header_types:
        raise HTTPException(status_code=400,
                            detail="Rendered media types are not allowed together with dicom media types.")
    return accept_headers

def accept_headers_instance(request: Request) -> AcceptHeaders:
    """
    Validates the accept headers in the request and returns the parsed accept headers.

    Args:
        request (Request): The incoming request.

    Raises:
        HTTPException: If the accept header is not present or contains an invalid media type.

    Returns:
        AcceptHeaders: The parsed accept headers.
    """



    if request.headers.get("accept",None) is None:
        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)
    accept_header_types = [x.type for x in accept_headers.accept_types]



    if DicomMediaType.ANY not in accept_header_types \
       and DicomMediaType.DICOM not in accept_header_types:
        if DicomMediaType.BYTES in accept_header_types:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={'Location': str(request.url)+'/bulkdata'})

        raise HTTPException(status_code=406,
                            detail="Invalid media type in accept header")

    if DicomMediaType.DICOM_IMAGE in accept_header_types:
        raise HTTPException(status_code=400,
                            detail="Rendered media types are not allowed together with dicom media types.")
    return accept_headers


def select_media_type_and_transfer_syntax_instance(sop_class_uid : str, accept_query : AcceptHeaders,
                                                   accept_headers : AcceptHeaders) -> str | None:
    """
    Selects the appropriate media type and transfer syntax for a DICOM instance
    based on the provided accept headers and query parameters.

    Args:
        sop_class_uid (str): The SOP class UID of the DICOM instance.
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        str: The selected transfer syntax, or `None` if no supported transfer syntax is found.
    """


    # 1. Identify the target's Resource Category
    # 2. Select the representation with the highest priority supported media type for that category in the
    #   Accept Query Parameter.
    # 3. If no media type in the Accept Query Parameter is supported, select the highest priority
    #   supported media type for that category in the Accept header field, if any.
    # 4. Otherwise, select the default media type for the category, if the Accept header field contains
    #   a wildcard media range matching the category, if any.
    # 5. Otherwise, return a 406 (Not Acceptable).
    # for instance types, this is not really important as will only be DICOM.
    # But Transfer syntax will be determined by this!


    sorted_accept_query = sorted(accept_query.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_query:
        #
        if accept_type.type == DicomMediaType.DICOM or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax :
                ## is this an acceptable transfer_syntax for this sopclass
                if is_supported_transfer_syntax(sop_class_uid,accept_type.transfer_syntax):
                    return accept_type.transfer_syntax
            else:
                return ExplicitVRLittleEndian # default transfer syntax



    sorted_accept_params = sorted(accept_headers.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_params:
        #
        if accept_type.type == DicomMediaType.DICOM or accept_type.type == DicomMediaType.ANY:
            ## we will not support the query parameter
            if accept_type.transfer_syntax :
                if is_supported_transfer_syntax(sop_class_uid,accept_type.transfer_syntax):
                    return accept_type.transfer_syntax
            else:
                return ExplicitVRLittleEndian # default transfer syntax

    return None  ## shoudl raise an error here




@wado_instance_router.get("/studies/{study_uid}", tags=["wado", "study"],
                          responses= {**inst_resp}
                          )
@wado_instance_router.get("/studies/{study_uid}/series", tags=["wado", "study"],
                          responses= {**inst_resp})

async def get_study_api(study_uid: str, request: Request,
                        accept_query : AcceptHeaders= Depends(parse_accept_charset_query),
                        accept_headers : AcceptHeaders = Depends(accept_headers_instance)) -> Response:
    """
    Retrieves the study with the given `study_uid` and packages the response using
    the provided `accept_headers`, `accept_query`, and `server_base_url`.

    Args:
        study_uid (str): The unique identifier of the study to retrieve.
        request (Request): The incoming request object.
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        The packaged response for the study.
    """

    insts = await request.state.data_service.get_study(study_uid)
    if len (insts) == 0:
        raise HTTPException(status_code=404,
                            detail="No instances found")
    return package_response_ps310(insts, accept_headers,accept_query,\
                                  request.state.server_base_url,request.state.codec_registry)

@wado_instance_router.get("/studies/{study_uid}/series/{series_uid}", tags=["wado", "series"],
                          responses= {**inst_resp})
async def get_series_api(study_uid: str, series_uid: str, request: Request,
                         accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
                         accept_headers : AcceptHeaders = Depends(accept_headers_instance)) -> Response:
    """
    Retrieves the series with the given `study_uid` and `series_uid`,
    and packages the response using the provided `accept_headers`, `accept_query`, and `server_base_url`.

    Args:
        study_uid (str): The unique identifier of the study to retrieve.
        series_uid (str): The unique identifier of the series to retrieve.
        request (Request): The incoming request object.
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        The packaged response for the series.
    """
        # will get the series and is multipart binary or bulk data
    # need to check the headers

    insts = await request.state.data_service.get_series(study_uid, series_uid)


    if len (insts) == 0:
        raise HTTPException(status_code=404,
                            detail="No instances found")
    return package_response_ps310(insts, accept_headers,accept_query,request.state.server_base_url,\
                                  request.state.codec_registry)

@wado_instance_router.get("/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}",tags=["wado","instance"],
                          responses= {**inst_resp})
async def get_instance_api(study_uid:str, series_uid:str, instance_uid:str, request: Request,
                           accept_query : AcceptHeaders = Depends(parse_accept_charset_query),
                           accept_headers : AcceptHeaders = Depends(accept_headers_instance)) -> Response:
    """
    Retrieves the instance with the given `study_uid`, `series_uid`, and `instance_uid`,
    and packages the response using the provided `accept_headers`, `accept_query`, and `server_base_url`.

    Args:
        study_uid (str): The unique identifier of the study to retrieve.
        series_uid (str): The unique identifier of the series to retrieve.
        instance_uid (str): The unique identifier of the instance to retrieve.
        request (Request): The incoming request object.
        accept_query (AcceptHeaders): The parsed accept headers from the query parameters.
        accept_headers (AcceptHeaders): The parsed accept headers from the request headers.

    Returns:
        The packaged response for the instance.
    """
        # will get the study
    inst = await request.state.data_service.get_instance(study_uid,series_uid,instance_uid)

    if not inst:
        raise HTTPException(status_code=404,
                            detail="No instances found")

    return package_response_ps310([inst], accept_headers,accept_query,\
                                  request.state.server_base_url,request.state.codec_registry)
