"""
    This module contains paths for the capability statement.
"""
import logging

from fastapi import APIRouter, Request, Depends, Response, HTTPException  # noqa

from app.utils.dicom_media import  DicomMediaType

from app.utils.accept_headers import parse_accept_headers

capabilities_router = APIRouter()
logger = logging.getLogger(__name__)


def accept_headers_capabilities(request: Request) -> DicomMediaType:
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
        if  accept.type == DicomMediaType.JSON or \
            accept.type == DicomMediaType.WADL:
            return accept.type
        if accept.type == DicomMediaType.ANY:
            return DicomMediaType.WADL
        logger.info("Invalid media type %s in accept header for Capability service.",accept.media_type_str)

    raise HTTPException(status_code=406,
            detail="Invalid media type in accept header")

@capabilities_router.options("/",tags=["capabilities"])
async def capabilities(request: Request,accept_type: DicomMediaType = Depends(accept_headers_capabilities)) -> Response:
    """
       Returns the capabilities statements
    Args:
        request (Request): The request object
    Returns:
        Response: response object with capabilities statement.
    """

    if accept_type == DicomMediaType.WADL:

        return Response(content=request.state.cap_statement_wadl,media_type="application/vnd.sun.wadl+xml")

    else:
        return Response(content=request.state.cap_statement_json,media_type="application/json")
