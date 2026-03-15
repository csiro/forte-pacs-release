"""
    This module contains handlers for qido paths if qido is configured.
    QIDO search queries are parsed and then passed to the configured query service.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schema.query import QueryLevel
from app.utils.openapi_metadata import standard_response
from .util import parse_query

qido_router = APIRouter()



@qido_router.get("/studies",tags=["qido","study"],responses= {**standard_response})
async def search_study_metadata_api(request: Request) -> JSONResponse:
    """Searches the study metadata based on the provided request parameters.

    This function extracts the limit, offset, and includefield parameters from the request query parameters,
    and then uses the `parse_query` function to curate the parameters for the study level query. It then
    calls the `query_study` method of the `query_service` to retrieve the study data, and maps the results
    to a DICOM JSON format before returning a JSON response.

    Args:
        request (Request): The HTTP request object containing the query parameters.

    Returns:
        JSONResponse: A JSON response containing the study metadata.
    """


    ## needs to return https://dicom.nema.org/dicom/2013/output/chtml/part18/sect_6.7.html#table_6.7.1-2
    ##

    params = MultiDict(request.query_params)
    limit = params.pop("limit",None)
    offset = params.pop("offset",None)
    include_field = params.poplist("includefield")  # pylint: disable=unused-variable

    ## check for any upsuported params
    curated_params = parse_query([QueryLevel.study],params)

    ## for all the params, map them onto the codes
    all_data = await request.state.query_service.query_study(curated_params,limit,offset)

    temp = []
    for aa in all_data:
        temp.append(aa.to_dicom_json(request.state.server_base_url))

    response = JSONResponse(temp)#content=cc,media_type=media_type)
    return response

    #    pass


@qido_router.get("/studies/{study_uid}/series",tags=["qido","study"],responses= {**standard_response})
@qido_router.get("/series",tags=["qido","series"],responses= {**standard_response})
async def search_series_metadata_api(request: Request, study_uid: str | None  = None)-> JSONResponse:
    """
    Searches the series metadata based on the provided request parameters.

    This function extracts the limit, offset, and includefield parameters from the request query parameters,
    and then uses the `parse_query` function to curate the parameters for the series level query. It then
    calls the `query_series` method of the `query_service` to retrieve the series data, and maps the results
    to a DICOM JSON format before returning a JSON response.

    Args:
        request (Request): The HTTP request object containing the query parameters.
        study_uid (str | None): The unique identifier of the study to filter the series search results.

    Returns:
        JSONResponse: A JSON response containing the series metadata.
    """


    params = MultiDict(request.query_params)
    limit = params.pop("limit",None)
    offset = params.pop("offset",None)
    include_field = params.poplist("includefield")  # pylint: disable=unused-variable

    levels = [QueryLevel.series]

    if study_uid or "StudyInstanceUID" in params.keys():
        levels.append(QueryLevel.study)


    curated_params = parse_query(levels,params)# fuzzy_matching,empty_value_matching,multi_value_matching)

    all_data = await request.state.query_service.query_series(curated_params,limit,offset,study_uid)

    temp = []

    for aa in all_data:
        temp.append(aa.to_dicom_json(request.state.server_base_url))

    response = JSONResponse(temp)#content=cc,media_type=media_type)
    return response


@qido_router.get("/studies/{study_uid}/series/{series_uid}/instances",tags=["qido","study"],
                 responses= {**standard_response})
@qido_router.get("/studies/{study_uid}/instances",tags=["qido","study"],responses= {**standard_response})
@qido_router.get("/instances",tags=["qido","study"],responses= {**standard_response})
async def search_instance_metadata_api(request: Request, study_uid: str | None = None,
                                       series_uid: str | None = None) -> JSONResponse:
    """
    Searches the instance metadata based on the provided request parameters.

    This function extracts the limit, offset, and includefield parameters from the request query parameters,
    and then uses the `parse_query` function to curate the parameters for the instance level query. It then
    calls the `query_instances` method of the `query_service` to retrieve the instance data, and maps the results
    to a DICOM JSON format before returning a JSON response.

    Args:
        request (Request): The HTTP request object containing the query parameters.
        study_uid (str | None): The unique identifier of the study to filter the instance search results.
        series_uid (str | None): The unique identifier of the series to filter the instance search results.

    Returns:
        JSONResponse: A JSON response containing the instance metadata.
    """

    print ("Inside")
    params = MultiDict(request.query_params)
    limit = params.pop("limit",None)
    offset = params.pop("offset",None)
    include_field = params.poplist("includefield")  # pylint: disable=unused-variable

    levels = [QueryLevel.instance]
    if study_uid:
        levels.append(QueryLevel.study)

    if series_uid:
        levels.append(QueryLevel.series)

    print ("Inside 34")

    curated_params = parse_query(levels,params)# fuzzy_matching,empty_value_matching,multi_value_matching)
    print ("Inside 2")

    all_data = await request.state.query_service.query_instances(curated_params,limit,offset,study_uid,series_uid)
    print ("Inside 3")

    temp = []

    for aa in all_data:
        temp.append(aa.to_dicom_json(request.state.server_base_url))

    response = JSONResponse(temp)#content=cc,media_type=media_type)
    return response
