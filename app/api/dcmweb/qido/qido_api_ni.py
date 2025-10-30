"""
    This module contains handlers that return 501 for qido paths if qido is not configured.
    This maybe be useful in contexts where the search functionality is not needed
    or implemented independant of this PACS system.
"""
from fastapi import APIRouter, Request
from app.utils.openapi_metadata import ni_resp
qido_router_ni = APIRouter()


@qido_router_ni.get("/studies",tags=["qido","study"],
    responses= {**ni_resp})
async def search_study_metadata_api(): # type: ignore
    """
        This Python function returns a 501 Not Implemented response,
        indicating that the search_study_metadata_api functionality is not configured.
    """



    return 501


@qido_router_ni.get("/studies/{study_uid}/series",tags=["qido","study"],
    responses= {**ni_resp})
@qido_router_ni.get("/series",tags=["qido","series"],
    responses= {**ni_resp})
async def search_series_metadata_api(request: Request, study_uid: str | None  = None) -> int:         # pylint: disable=unused-argument

    """
        This Python function returns a 501 Not Implemented response,
        indicating that the search_study_metadata_api functionality is not configured.
    """


    return 501


@qido_router_ni.get("/studies/{study_uid}/series/{series_uid}/instances",tags=["qido","study"],
    responses= {**ni_resp})
@qido_router_ni.get("/studies/{study_uid}/instances",tags=["qido","study"],
    responses= {**ni_resp})
@qido_router_ni.get("/instances",tags=["qido","study"],
    responses= {**ni_resp})
async def search_instance_metadata_api(request: Request, study_uid: str | None = None, # pylint: disable=unused-argument
                                       series_uid: str | None = None) -> int: # pylint: disable=unused-argument
    """
        This Python function returns a 501 Not Implemented response,
        indicating that the search_study_metadata_api functionality is not configured.
    """
    return 501
