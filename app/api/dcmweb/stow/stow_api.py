"""
This module contains handlers for stow paths.
STOW queries are parsed and then passed to the configured data service.

"""

import random
import string
import json
import base64
from typing import Dict, List, Tuple, Any
from xml.etree import ElementTree
import logging
from dataclasses import dataclass
import pydicom
from pydicom.uid import ExplicitVRLittleEndian
from fastapi import APIRouter, Request, Depends, Response, HTTPException  # noqa


from app.utils.dicom_media import DicomMediaMultipartParser, \
    DicomMediaSinglepartParser, DicomMediaType, DicomMediaPartXML

from app.utils.dicom_storage_sop_class import \
    is_supported_stow_sop_class, is_encapsulated_document_class, \
    is_image_sop_class, is_supported_stow_transfer_syntax, \
    is_compressed_transfer_syntax
from app.schema.dicom_instance import DCMInstance
from app.schema.dicom_pixel_data import DCMPixelData

from app.utils.pixel_data_handlers import parse_ps310_pixel_data, \
    parse_uncompressed_bulk_pixel_data, parse_compressed_bulk_pixel_data, \
    parse_compressed_bulk_video_data

from app.utils.xml_json_converters import xml_to_json, json_to_xml
from app.utils.accept_headers import parse_accept_headers

from app.config import settings

from app.utils.metadata_utils import combine_metadata
from app.utils.openapi_metadata import standard_response, stow_request_representation

stow_router = APIRouter()
logger = logging.getLogger(__name__)

@dataclass
class BulkURIItem:
    """Represents a bulk data URI item for STOW operations.

    This dataclass holds information about a DICOM instance and its
    associated bulk data URI, including whether the data was found,
    the new URL location, and pixel data format details.

    Attributes:
        instance (DCMInstance): The DICOM instance object
        found (bool): Whether the bulk data was found
        new_url (str): The new URL location for the bulk data
        is_pixel (bool): Whether this item contains pixel data
        pixel_data_format (str): The format of the pixel data
    """
    instance: DCMInstance
    found: bool
    new_url: str
    is_pixel: bool
    pixel_data_format: str


def accept_headers_stow(request: Request) -> DicomMediaType:
    """Get valid headers for STOW request

    Args:
        request (Request): The request object
    Returns:
        DicomMediaType: The valid DicomMediaType
    Raises:
        HTTPException: 406 if no valid accept headers present
    """

    if request.headers.get("accept", None) is None:
        logger.error("No accept headers present in Request %s",Request.url)

        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)

    sorted_accept_headers = sorted(accept_headers.accept_types,\
        key=lambda x: x.quality,reverse=True) ## currently only

    for accept in sorted_accept_headers:
        if  accept.type == DicomMediaType.DICOM_JSON or \
            accept.type == DicomMediaType.DICOM_XML:
            return accept.type
        if accept.type == DicomMediaType.ANY:
            return DicomMediaType.DICOM_XML
        logger.info("Invalid media type %s in accept header for STOW",accept.media_type_str)

    raise HTTPException(status_code=406,
            detail="Invalid media type in accept header")


def get_content_type(request: Request) -> Tuple[DicomMediaType | None, str|None,str|None, str|None]:
    """ Get the content type from the request.

    Args:
        request (Request): Request object

    Returns:
        Tuple[DicomMediaType | None, str|None,str|None, str|None]:
            Tuple with DicomMediaType, boundary, transfer_syntax_uid, charset
    """
    # check here
    # https://stackoverflow.com/questions/67932330/how-to-restrict-content-type-in-fastapi-request-header

    ct = request.headers['content-type'].split(';')

    ct_type = ct[0]

    sub_headers = {}

    for header in ct[1:]:
        temp = header.split('=')
        sub_headers[temp[0].lower().strip()] = temp[1]

    transfer_syntax_uid = sub_headers.get("transfer-syntax", None)
    charset = sub_headers.get("charset", None)
    media_type = None
    temp_boundary  = sub_headers.get('boundary', None)
    boundary = temp_boundary.strip('"') if temp_boundary \
        else temp_boundary ## this will make my head spin later

    # check if there is a transfer syntax
    if "multipart/related" in ct_type:
        media_type = DicomMediaType.MULTIPART

    elif ct_type == '"application/dicom"':
        media_type = DicomMediaType.DICOM

    elif ct_type == '"application/dicom+json"':
        media_type = DicomMediaType.DICOM_JSON

    elif ct_type == '"application/dicom+xml"':
        media_type = DicomMediaType.DICOM_XML

    return (media_type, boundary, transfer_syntax_uid, charset)


# We are using the spec here
# https://dicom.nema.org/medical/dicom/2022d/output/chtml/part18/sect_10.5.html
# as the basis for this.
#
@stow_router.post("/studies", tags=["stow", "study"],
                  responses={**standard_response}, openapi_extra=stow_request_representation)
@stow_router.post("/studies/{study_uid}", tags=["stow", "study"],responses={**standard_response},
                  openapi_extra=stow_request_representation)
async def stow_study_api(request: Request,
                         dicom_media_type: Tuple[DicomMediaType, str, str, str]
                         = Depends(get_content_type),
                         study_uid: str | None = None,
                         accept_type: DicomMediaType = Depends(accept_headers_stow)) -> Response:  # noqa
    """ Route to handle STOW-RS.

    Args:
        request (Request): request object
        dicom_media_type (Tuple[DicomMediaType, str, str, str], optional): dicom media type of the request.
            Extracted from request using get_content_type.
        study_uid (str, optional): study uid . Defaults to None.
        accept_type (DicomMediaType, optional): accept type of the request.
            Extracted from request using accept_headers_stow.
    Returns: response object with report for stow operation.

    """
    # will get the study and is multi-part binary or bulk data
    # need to check the headers

    content_type = dicom_media_type[0]
    boundary = dicom_media_type[1]
    transfer_syntax_uid = dicom_media_type[2]
    charset = dicom_media_type[3]  ## we ignore the charset as the instance is converted to UTF-8 and stored.


    instances = []
    base_url = request.state.server_base_url

    parser : DicomMediaMultipartParser| DicomMediaSinglepartParser | None = None

    if content_type != DicomMediaType.MULTIPART:
        parser = DicomMediaSinglepartParser(content_type, transfer_syntax_uid)
    else:
        parser = DicomMediaMultipartParser(boundary)

    bulk_uris = {}

    failed_sops = []
    referenced_sops = []
    other_failures = []

    parts = parser.parse_body(await request.body())


    # have a list of parts
    for part in parts:

        if part.content_type() == DicomMediaType.DICOM:
            # need to be consistent between

            if part.data is None:
                # we can't parse the ps310 dataset. Set a general failure
                err = {}
                err["00081197"] = {"vr": "US", "Value": [272]}
                other_failures.append(err)

            else:

                (instance,errors) = handle_ps310_dataset(part.data, base_url)
                instances.append(instance)
                failed_sops.extend(errors)

        elif part.content_type() in \
                [DicomMediaType.DICOM_JSON, DicomMediaType.DICOM_XML]:
            # this is meta data
            # need to parse any bulkdata URIS
            (instances_local, instance_bulk_uris) = handle_metadata(
                part.data,
                part.content_type(),
                transfer_syntax_uid,
                base_url)

            if content_type != DicomMediaType.MULTIPART:
                if instance_bulk_uris:


                    # singel part message can only have inline data.
                    error = gen_ref_sop(instance.sop_class_uid,
                                        instance.instance_uid)
                    error["00081197"] = {"vr": "US", "Value": [49152]}
                    failed_sops.append(error)
                    continue

            instances.extend(instances_local)
            bulk_uris.update(instance_bulk_uris)

        else:

            if content_type != DicomMediaType.MULTIPART:

                # single part message can only have inline data.
                err = {}
                err["00081197"] = {"vr": "US", "Value": [49153]}
                other_failures.append(err)

            uri_full = part.headers["content-location"]
            (uri, uri_frame_number) = parse_frame_uri(uri_full)
            buri = bulk_uris[uri]
            instance = buri.instance
            new_url = buri.new_url


            # The Encapsulated Document (0042,0011) Bulkdata element shall
            # be encoded using the media-type from the Media Type of the
            # Encapsulated Document (0042,0012) Attribute with one
            # representation per document.
            if part.content_type() == DicomMediaType.DICOM_DOCUMENT:
                if not instance.other_bulk_data:
                    instance.other_bulk_data = {}
                instance.other_bulk_data[new_url] = part.data
                instance.encap_document_mediatype = part.content_type_str()
                buri.found = True

            # Uncompressed Bulkdata (including pixel data but with
            # the exception of the Encapsulated Document (0042,0011)
            # element) shall be encoded as application/octet-stream
            # with one representation per Bulkdata item.
            elif part.content_type() in [DicomMediaType.BYTES]  and not buri.is_pixel:

                if not instance.other_bulk_data:
                    instance.other_bulk_data = {}
                instance.other_bulk_data[new_url] = part.data

                buri.found = True

            ###

            if instance.pixel_data is not None:

                if part.content_type() in [DicomMediaType.BYTES]  and  buri.is_pixel:

                        # only uncompressed, explicit VR, little endian.

                        # need to check number of expected frames
                    instance.pixel_data.frames = parse_uncompressed_bulk_pixel_data(part.data, \
                        instance.pixel_data.number_of_frames)  # noqa
                    instance.pixel_data.pixel_data_format = buri.pixel_data_format


                    buri.found = True
                # Compressed pixel data for a Single Frame Image shall be
                # encoded as one compressed Bulkdata representation.

                # Compressed pixel data for a Multi-Frame Image shall be
                # encoded as multiple Single Frame Image compressed
                # Bulkdata representations.
                elif part.content_type() == DicomMediaType.DICOM_IMAGE:
                    ## if we accept gif and png, then we have to
                    ## transform them

                    ## and also create an image pixel description macro
                    ## https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.3.3.html

                    if uri_frame_number == 0:  ## on teh first frame, we need to get all the meta data.

                        ## changes instance in place
                        parse_compressed_bulk_pixel_data(part,instance,\
                            buri.pixel_data_format, request.state.codec_registry)

                    # pixel meta data should be grabbed from the image itself
                    # we will use image codecs to get it
                    else:
                        if part.content_type_str() in ["image/png","image/gif"]:
                            dcm_pixel = request.state.codec_registry.decode_png_gif(part.data,part.content_type_str())
                            instance.pixel_data.frames[uri_frame_number] = dcm_pixel.tobytes()
                        else:
                            instance.pixel_data.frames[uri_frame_number] = part.data

                    buri.found = True

                # Compressed pixel data for a Video shall be
                # encoded as one compressed Bulkdata representation.
                elif part.content_type() == DicomMediaType.DICOM_VIDEO:  # also pixel
                    # start looking at https://dicom.nema.org/medical/dicom/2019a/output/chtml/part05/sect_8.2.5.html
                    # this is a video
                    instance.pixel_data.frames = [part.data]
                    instance.pixel_data.pixel_data_format = buri.pixel_data_format
                    parse_compressed_bulk_video_data(part,instance,buri.pixel_data_format)
                    buri.found = True

            else:
                ## TODO : fix with accurate error log
                logger.error("pixel data is none")




    missing_buri = []
    # check that all bulk uris have been found
    for buri,key in bulk_uris.items(): #pylint: disable=unused-variable
        if not buri.found:
            ##
            instance = buri.instance
            if instance.pixel_data is not None:

                missing_buri.append((instance.sop_class_uid, instance.pixel_data.transfer_syntax_uid, \
                    instance.instance_uid))  # noqa
            else:
                missing_buri.append((instance.sop_class_uid, ExplicitVRLittleEndian, \
                    instance.instance_uid))  # noqa
    all_meta_data = []
    # store all the instance
    global_study_uid = None
    for instance_ in instances:
        instance = instance_

        if global_study_uid and (instance.study_uid != global_study_uid):

            raise HTTPException(status_code=409,detail="Study UID is not unique in instances.")
        else:
            global_study_uid=instance.study_uid


    for instance_ in instances:
        instance = instance_
        sop_class_uid = instance.sop_class_uid
        inst_transfer_syntax_uid =  str(ExplicitVRLittleEndian)
        if instance.pixel_data is not None and  instance.pixel_data.transfer_syntax_uid is not None:
            #logger.warning ("Saved TS is %s "%(instance.pixel_data.transfer_syntax_uid))
            inst_transfer_syntax_uid = instance.pixel_data.transfer_syntax_uid
        sop_instance_uid = instance.instance_uid

        if global_study_uid and instance.study_uid != study_uid:
            pass
        else:
            global_study_uid=instance.study_uid

        if (sop_class_uid, inst_transfer_syntax_uid, sop_instance_uid) \
                in missing_buri:
            err = gen_ref_sop(sop_class_uid, sop_instance_uid)
            # change this
            err["00081197"] = {"vr": "US", "Value": [-1]}
            failed_sops.append(err)
            continue

        # check for supported transfer syntax uids
        if not is_supported_stow_transfer_syntax(inst_transfer_syntax_uid):
            # return an error
            # status code 49442
            # https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_I.2.2.html
            err = gen_ref_sop(sop_class_uid, sop_instance_uid)
            err["00081197"] = {"vr": "US", "Value": [49442]}
            failed_sops.append(err)
            continue

            # is this a supported sop class?
        if not is_supported_stow_sop_class(sop_class_uid):
            # return an error code
            # status code 290
            # https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_I.2.2.html
            err = gen_ref_sop(sop_class_uid,sop_instance_uid)
            err["00081197"] = {"vr": "US", "Value": [290]}
            failed_sops.append(err)
            continue

        if is_compressed_transfer_syntax(inst_transfer_syntax_uid):
            if not is_image_sop_class(sop_class_uid):
                # error only image types can have compressed transfer syntax
                # status code 49442
                # https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_I.2.2.html
                err = gen_ref_sop(sop_class_uid, sop_instance_uid)
                err["00081197"] = {"vr": "US", "Value": [49442]}
                errors.append(err)

                continue

        if is_image_sop_class(sop_class_uid):
            if instance.pixel_data is None or None in instance.pixel_data.frames:
                # missing pixel data or missing frames.
                val = 43264
                if instance.pixel_data and None in instance.pixel_data.frames:
                    val = -1

                err = gen_ref_sop(sop_class_uid, sop_instance_uid)
                err["00081197"] = {"vr": "US", "Value": [val]}
                failed_sops.append(err)
                continue



        # need a try block for this. Failed

        # if we need to convert the images, that should happen here


        await request.state.data_service.store_instance(instance)

        instance_uri = base_url+"/"+settings.wado_prefix+\
            f"/studies/{instance.study_uid}/series/{instance.series_uid}/instances/{instance.instance_uid}/"

        referenced_sops.append(gen_ref_sop(sop_class_uid, sop_instance_uid, instance_uri))
        combined_metadata = combine_metadata(instance)
        all_meta_data.append(combined_metadata)

    if settings.query_service != "none":
        for call_back in request.state.stow_callbacks:  ## this needs to be abstracted
            await request.state.queue_service.enqueue_task(settings.qido_queue_name,call_back, all_meta_data)

    # this needs to be updated as per
    # https://dicom.nema.org/medical/dicom/2019a/output/chtml/part18/sect_6.6.html
    # https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_10.5.3.html
    json_response = {}

    any_errors = False
    if len(failed_sops) != 0:
        json_response["00081198"] = {"vr":"SQ", "Value": failed_sops}
        any_errors=True
    if len(referenced_sops) != 0:
        json_response["00081199"] = {"vr":"SQ", "Value":referenced_sops}
        study_url = base_url+"/"+settings.wado_prefix+"/studies/"+global_study_uid
        json_response["00081190"] = {"vr": "UR", "Value": [study_url]}
    if len(other_failures) != 0:
        json_response["0008119A"] = {"vr":"SQ", "Value":other_failures}
        any_errors=True

    status_code = 200
    if any_errors:
        status_code = 202

    # https://dicom.nema.org/medical/dicom/current/output/html/part18.html#table_10.5.3-1
    if accept_type == DicomMediaType.DICOM_XML:

        xml_ele = json_to_xml(json_response)

        xml_str = ElementTree.tostring(xml_ele,encoding="utf-8")

        part = DicomMediaPartXML(xml_str)

        response = Response(content=xml_str, status_code=status_code,media_type="application/dicom+xml")

    else:


        cc = json.dumps([json_response])

        response = Response(content=cc, status_code=status_code,media_type="application/dicom+json")

    # content=cc,media_type=media_type)

    return response


def handle_ps310_dataset(dataset: pydicom.Dataset, base_url: str) -> Tuple[DCMInstance, List[Dict[str, Dict]]]:
    """
    Handles the processing of a DICOM dataset in the PS3.10 format,
    including extracting metadata, pixel data, and other bulk data.
    This function constructs a `DCMInstance` object from the dataset,
    which can be used for further processing or storage.

    Args:
        dataset (pydicom.Dataset): The DICOM dataset in PS3.10 format.
        base_url (str): The base URL for constructing URIs for the DICOM instance.

    Returns:
        Tuple[DCMInstance, List[Dict[str, Dict]]]: A tuple containing the constructed `DCMInstance` object
        and a list of any errors encountered during processing encoded as DICOM JSON.
    """

    study_uid = dataset.StudyInstanceUID
    series_uid = dataset.SeriesInstanceUID
    instance_uid = dataset.SOPInstanceUID


    sop_class_uid = dataset.SOPClassUID
    transfer_syntax_uid = dataset.file_meta.TransferSyntaxUID
    errors : List[Dict[str, Dict]] = []

    uri = base_url+f"/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/"

    bulk_data = {}

    seen_tags = []
    pixel_data_format = "INT"
    pixel_data_raw = bytes()

    def bulk_data_handler(data_element : pydicom.DataElement) -> str:
        tag_str = f"{data_element.tag.group:04X}{data_element.tag.elem:04X}"

        bd_uri = uri

        if tag_str in ["7FE00010", "7FE00008", "7FE00009"]:
            nonlocal pixel_data_format

            # can only have int, float or double data
            if tag_str == "7FE00008":
                pixel_data_format = "FLOAT"
            elif tag_str == "7FE00009":
                pixel_data_format = "DOUBLE"

            bd_uri = uri+'pixel_data'
            nonlocal pixel_data_raw
            pixel_data_raw = data_element.value
        else:
            # need a random string here as well

            while tag_str in seen_tags:  # this is a hack atm
                tag_str = tag_str+'_'+''.join(random.choices(
                    string.ascii_uppercase + string.digits, k=4))
            seen_tags.append(tag_str)
            bulk_data[tag_str] = data_element.value
            bd_uri = uri+'bulkdata/'+tag_str

        return bd_uri

    meta_data_inst = dataset.to_json_dict(bulk_data_threshold=0,
                                bulk_data_element_handler=bulk_data_handler)
    instance = DCMInstance.model_construct(study_uid=study_uid,
                           series_uid=series_uid,
                           instance_uid=instance_uid,
                           sop_class_uid=sop_class_uid)

    if is_image_sop_class(sop_class_uid):  # this includes video

        number_of_frames = 1
        try:
            number_of_frames = dataset.NumberOfFrames
        except AttributeError:
            pass

        # if multi_frame and

        instance.pixel_data = generate_pixel_data_object(meta_data_inst,transfer_syntax_uid)

        pixel_data_frames = parse_ps310_pixel_data(pixel_data_raw,
                                                  number_of_frames,
                                                  transfer_syntax_uid)

        instance.pixel_data.pixel_data_format = pixel_data_format
        instance.pixel_data.frames = pixel_data_frames

        # check that frames match


    # check if this is encapsulated
    if is_encapsulated_document_class(sop_class_uid):
        instance.encap_document_mediatype = \
            dataset.MediaTypeOfEncapsulatedDocument

    instance.meta_data=json.dumps(meta_data_inst)
    instance.other_bulk_data = bulk_data

    return (instance, errors)


def handle_metadata(data: str, content_type: DicomMediaType, transfer_syntax_uid: str,base_url: str) \
        -> Tuple[List, Dict]:
    """
    Handles the processing of DICOM metadata and associated bulk data for STOW-RS requests.

    Args:
        data (str): The DICOM metadata, either in JSON or XML format.
        content_type (DicomMediaType): The media type of the DICOM metadata.
        transfer_syntax_uid (str): The transfer syntax UID of the DICOM metadata.
        base_url (str): The base URL for the STOW-RS request.

    Returns:
        Tuple[List, Dict]: A tuple containing a list of `DCMInstance` objects and a dictionary of bulk data URIs.
    """

    meta_data_insts = None
    insts = []
    bulk_uris = {}

    if content_type == DicomMediaType.DICOM_JSON:
        # can have multiple meta data insts
        meta_data_insts = json.loads(data.strip())# this will be an array
        if not isinstance(meta_data_insts,list):
            meta_data_insts= [meta_data_insts]
    else:
        # can have only one
        element = ElementTree.fromstring(data)
        meta_data_insts = [xml_to_json(element)]


    for meta_data_inst in meta_data_insts:


        study_uid = meta_data_inst["0020000D"]["Value"][0]
        series_uid = meta_data_inst["0020000E"]["Value"][0]
        instance_uid = meta_data_inst["00080018"]["Value"][0]
        instance_sop_class_uid = meta_data_inst["00080016"]["Value"][0]
        # transfer_syntax_uid = part.data.TransferSyntaxUID
        #  need this or not compliant
        #  The application/dicom+xml and application/dicom+json Media Types
        #  may have a Transfer Syntax parameter in order to specify
        # the encoding of base64 data.


        # need to fix from here
        instance = DCMInstance.model_construct(study_uid=study_uid,
                               series_uid=series_uid,
                               instance_uid=instance_uid,
                               sop_class_uid=instance_sop_class_uid,
        )

        ## these values will be overwritten

        ## only if this has pixel data
        if is_image_sop_class(instance_sop_class_uid):
            instance.pixel_data = generate_pixel_data_object(meta_data_inst,transfer_syntax_uid)
        #instance.pixel_data = [None]*number_of_frames

        # instance.transfer_syntax_uid=transfer_syntax_uid
        inst_bulk_uris = get_bulk_and_inline_data(meta_data_inst,
                                                  base_url,
                                                  instance)

        ## remove all the bits related to pixel data
        instance.meta_data = json.dumps(meta_data_inst)

        # check that frames match

        # check if this is encapsulated
        if is_encapsulated_document_class(instance_sop_class_uid):
            med_encap = meta_data_inst["00420012"]["Value"][0]
            instance.encap_document_mediatype = med_encap

        insts.append(instance)
        bulk_uris.update(inst_bulk_uris)

    return (insts, bulk_uris)


def gen_ref_sop(sopclass_uid: str, sopinstance_uid: str, uri: str | None = None) \
        -> Dict[str, Dict]:
    """
        Generate a reference SOP (Service-Object Pair) dictionary with the provided SOP class UID
        and SOP instance UID, and an optional URI.

        Args:
            sopclass_uid (str): The SOP class UID.
            sopinstance_uid (str): The SOP instance UID.
            uri (str, optional): The URI associated with the SOP instance.

        Returns:
            Dict[str, Dict]: A dictionary containing the reference SOP information.
    """

    temp = {}
    temp["00081150"] = {"vr": "UI", "Value": [sopclass_uid]}
    temp["00081155"] = {"vr": "UI", "Value": [sopinstance_uid]}
    if uri:
        temp["00081190"] = {"vr": "UR", "Value": [uri]}

    return temp


def _get_number_of_frames(json_meta: Dict) -> int:
    """
    Get the number of frames in the DICOM image metadata.

    Args:
        json_meta (Dict): The DICOM image metadata in JSON format.

    Returns:
        int: The number of frames in the DICOM image.
            If the number of frames cannot be determined from the metadata, returns 1.
    """


    try:
        return int(json_meta["00280008"]["Value"][0])
    except KeyError:
        return 1


# this modifies the dataset
def get_bulk_and_inline_data(ds: Dict, uri: str, instance: DCMInstance
                             ) -> Dict[str, BulkURIItem]:
    """
    This function processes the DICOM dataset and extracts the bulk data and inline binary data.
    It handles pixel data and other bulk data separately, updating the provided DCMInstance object accordingly.

    Args:
        ds (Dict): The DICOM dataset in dictionary format.
        uri (str): The URI associated with the DICOM instance.
        instance (DCMInstance): The DCMInstance object to be updated with the extracted data.

    Returns:
        Dict[str, Dict]: A dictionary containing the bulk data URIs and their associated metadata.
    """

    bk = {}

    seen_tags = []

    for ele_key in ds:

        # if pixel data
        # treat differently
        ele = ds[ele_key]
        ele_vr = ele.get("VR",ele.get("vr",None))
        if ele_vr == "SQ" :
            for ii in ele["Value"]:
                bk.update(get_bulk_and_inline_data(ii, uri, instance))
        else:
            tag_str = ele_key
            replace_uri = ""

            is_pixel = False
            pixel_data_format = "INT"
            if tag_str in ["7FE00010", "7FE00008", "7FE00009"]:

                if tag_str == "7FE00008":
                    pixel_data_format = "FLOAT"
                elif tag_str == "7FE00009":
                    pixel_data_format = "DOUBLE"

                replace_uri = uri+'pixel_data'
                is_pixel = True

            else:
                while tag_str in seen_tags:  # this is a hack atm
                    tag_str = tag_str + '_' + \
                        ''.join(random.choices(string.ascii_uppercase +
                                               string.digits, k=4))
                seen_tags.append(tag_str)

                replace_uri = uri+'bulkdata/'+tag_str


            if "InlineBinary" in ele:
                # decode the inline binaries
                value = base64.b64decode(ele["InlineBinary"])
                # delete inline binary and
                del ele["InlineBinary"]

                if is_pixel:
                    if instance.pixel_data:
                        instance.pixel_data.frames = parse_uncompressed_bulk_pixel_data(
                            value, _get_number_of_frames(ds))
                        instance.pixel_data.pixel_data_format = pixel_data_format
                        instance.pixel_data.number_of_frames = _get_number_of_frames(ds)
                else:
                    if not instance.other_bulk_data:
                        instance.other_bulk_data={}
                    instance.other_bulk_data[replace_uri] = value

            elif "BulkDataURI" in ele:

                bk[ele["BulkDataURI"]] = BulkURIItem(instance=instance,found=False,new_url=replace_uri,\
                                                     is_pixel=is_pixel,pixel_data_format=pixel_data_format)


                ele["BulkDataURI"] = replace_uri

    return bk



def parse_frame_uri(uri_full : str) -> Tuple[str,int]: ## TODO fix this
    """
    The `parse_frame_uri` function takes a full URI string and returns a tuple containing the URI and the frame index.

    Args:
        uri_full (str): The full URI string to be parsed.

    Returns:
        Tuple[str, int]: A tuple containing the URI and the frame index.
    """

    return (uri_full,0)


def pop_tag(dict_: Dict , tag_key : str, get_val : bool =True)->Any:
    """
    Pops a DICOM tag from the provided dictionary and returns its value.

    Args:
        dict_ (dict): The dictionary containing the DICOM tags.
        tag_key (str): The key of the DICOM tag to be popped.
        get_val (bool, optional): If True, returns the first value in the "Value" list of the DICOM tag.
            If False, returns the entire "Value" list. Defaults to True.

    Returns:
        Any or None: The value of the DICOM tag, or None if the tag is not found.
    """


    tag = dict_.pop(tag_key,None)

    if not tag:
        return None

    if get_val:
        return tag["Value"][0]
    else:
        return tag["Value"]


## TODO needs to be fixed up
def generate_pixel_data_object(meta_data_inst : Dict ,transfer_syntax_uid : str) -> DCMPixelData:
    """
    Generates a DCMPixelData object from the provided metadata instance and transfer syntax UID.

    Args:
        meta_data_inst (dict): A dictionary containing the DICOM metadata.
        transfer_syntax_uid (str): The transfer syntax UID for the DICOM data.

    Returns:
        DCMPixelData: A DCMPixelData object with the parsed pixel data information.
    """


    temp = {}
    temp["samples_per_pixel"] = pop_tag(meta_data_inst,"00280002") # does not change

    temp["photometric_interpretation"] = pop_tag(meta_data_inst,"00280004")
    if temp["samples_per_pixel"] > 1:
        temp["planar_configuration"] = pop_tag(meta_data_inst,"00280006") # required if samples per pixel > 1

    temp["rows"] = pop_tag(meta_data_inst,"00280010") # does not change
    temp["columns"] = pop_tag(meta_data_inst,"00280011") # does not change
    ## ignore pixel aspect ratio for now

    temp["bits_allocated"] = pop_tag(meta_data_inst,"00280100") # does not chnage
    temp["bits_stored"] = pop_tag(meta_data_inst,"00280101")
    temp["high_bit"] = pop_tag(meta_data_inst,"00280102")
    temp["pixel_representation"] = pop_tag(meta_data_inst,"00280103")

    #transfer_syntax_uid = pop_tag("")

    temp["smallest_image_pixel_value"] = pop_tag(meta_data_inst,"00280106")
    temp["largest_image_pixel_value"] = pop_tag(meta_data_inst,"00280107")
    # ignore pixel_padding_range_limit for now


    # shouldn't pop
    temp["number_of_frames"] = _get_number_of_frames(meta_data_inst)


    temp["transfer_syntax_uid"]=transfer_syntax_uid

    if not temp["number_of_frames"]:
        temp["number_of_frames"] = 1

    if temp["photometric_interpretation"] == "PALETTE COLOR":
        temp["red_palette_color_lookup_table_descriptor"] = pop_tag(meta_data_inst,"00281101",False)
        temp["blue_palette_color_lookup_table_descriptor"] =  pop_tag(meta_data_inst,"00281102",False)
        temp["green_palette_color_lookup_table_descriptor"] = pop_tag(meta_data_inst,"00281103",False)

        temp["red_palette_color_lookup_table_data"] = pop_tag(meta_data_inst,"00281201")
        temp["blue_palette_color_lookup_table_data"] = pop_tag(meta_data_inst,"00281202")
        temp["green_palette_color_lookup_table_data"] = pop_tag(meta_data_inst,"00281203")

    pixel_data_object = DCMPixelData.model_construct(** temp)
    pixel_data_object.frames = [b"\0"]*pixel_data_object.number_of_frames

    return pixel_data_object
    # ignore for now
    # icc_profile: Optional[bytes]
    # color_space: Optional[str]
