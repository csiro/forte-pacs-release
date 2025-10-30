"""
    This module contains handlers for qido paths if qido is configured.
    QIDO search queries are parsed and then passed to the configured query service.
"""
from typing import List
from fastapi import APIRouter, Request,  HTTPException
from fastapi.responses import JSONResponse
from starlette.datastructures import MultiDict
from app.schema.query import MatchType,QueryLevel, QueryAttributeMatch
from app.utils.openapi_metadata import standard_response

qido_router = APIRouter()

## Study level sttributes that can be searched.
study_level_attrs = {
    "StudyDate":("00080020","DA",QueryLevel.study),
    "StudyTime":("00080030","TM",QueryLevel.study),
    "AccessionNumber":("00080050", "SH", QueryLevel.study),
    "ModalitiesInStudy":("00080061","CS", QueryLevel.study),
    "ReferringPhysicianName":("00080090","PN", QueryLevel.study),
    "PatientName":("00100010","PN", QueryLevel.study),
    "PatientID":("00100020","LO", QueryLevel.study),
    "StudyInstanceUID":("0020000D","UI",QueryLevel.study),
    "StudyID":("00200010","SH",QueryLevel.study)

}

## Series level attributes that can be searched
series_level_attrs = {
    "Modality":("00080060","CS",QueryLevel.series),
    "SeriesInstanceUID":("0020000E","UI",QueryLevel.series),
    "SeriesNumber":("00200011","IS",QueryLevel.series),
    "PerformedProcedureStepStartDate":("00400244","DA",QueryLevel.series),
    "PerformedProcedureStepStartTime":("00400245","TM",QueryLevel.series)

}

## Instance level attributes that can be searched.

instance_level_attrs = {
    "SOPClassUID":("00080016","UI",QueryLevel.instance),
    "SOPInstanceUID":("00080018","UI",QueryLevel.instance),
    "InstanceNumber":("00200013","IS",QueryLevel.instance)
}


all_tags = study_level_attrs|series_level_attrs|instance_level_attrs
attr_tags = {val[0]: key for key,val in all_tags.items()}


def parse_query(levels : List[QueryLevel],params: MultiDict) -> List[QueryAttributeMatch]:
    """
    Parses the query parameters from the request and returns a list of `QueryAttributeMatch` objects that represent the
    search criteria for the QIDO-RS query.

    This function extracts the `fuzzymatching`, `emptyvaluematching`, and `multivaluematching` parameters
    from the request and uses them to determine the appropriate `MatchType` for each query parameter.
    It then maps the query parameters to the corresponding DICOM attribute tags and creates
    a `QueryAttributeMatch` object for each parameter.

    The function also performs some validation to ensure that the query parameters are supported for the requested
    Information Entity (IE) level.

    Args:
        levels (List[QueryLevel]): The list of IE levels for which the query parameters should be parsed.
        params (MultiDict): The query parameters from the request.

    Returns:
        List[QueryAttributeMatch]: A list of `QueryAttributeMatch` objects representing the search criteria.
    """




    fuzzy_matching = params.pop("fuzzymatching","false")
    empty_value_matching = params.pop("emptyvaluematching",False)
    multi_value_matching = params.pop("multivaluematching",False)  # pylint: disable=unused-variable


    attr_names = all_tags.keys()

    parsed_params = []

    for pk in params.keys():

        query_tag = None
        if pk in attr_names:
            query_tag=pk
        elif pk in attr_tags.keys():
            query_tag=attr_tags[pk]
        else:
            raise HTTPException(status_code=400,detail=f"Query parameter ({query_tag}) is not supported for QIDO RS")


        level = all_tags[query_tag][2]

        if level not in levels:
            ## log error
            raise HTTPException(status_code=400,\
                detail=f"Query parameter ({query_tag}) is not supported for QIDO-RS at the requested IE Level {level}")

        vr_tag = all_tags[query_tag][1]

        value = params[pk]

        match_type = MatchType.single_value
        if vr_tag in ["AE","CS","LO","LT","PN","SH","UC","UT"]:
            if "*" in value or "?" in value:
                ## this is wildcard
                if value == "*":
                    match_type=MatchType.universal
                else:
                    match_type=MatchType.wildcard

            elif value == "\"\"" :
                ## this is empty
                if empty_value_matching:
                    match_type=MatchType.empty
                else:
                    continue
            else:
                if vr_tag == "PN" and fuzzy_matching:
                    match_type=MatchType.fuzzy
                else:
                    match_type=MatchType.single_value


        elif vr_tag in ["DA","TM","DT"]:

            if "-" in value:
                match_type=MatchType.range
                ## this is a range
            else:
                match_type=MatchType.single_value

        elif vr_tag == "SQ":
            match_type=MatchType.sequence

        elif value == "":
            match_type=MatchType.universal
        elif vr_tag == "UI":
            if '\\' in value:
                match_type=MatchType.list_of_uid
                value = value.split('\\')
        else:
            match_type=MatchType.single_value


        parsed_params.append(QueryAttributeMatch(match_type,level,query_tag,value))

    return parsed_params

## we don't support multi value mathcing


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

    params = MultiDict(request.query_params)
    limit = params.pop("limit",None)
    offset = params.pop("offset",None)
    include_field = params.poplist("includefield")  # pylint: disable=unused-variable

    levels = [QueryLevel.instance]
    if study_uid:
        levels.append(QueryLevel.study)

    if series_uid:
        levels.append(QueryLevel.series)


    curated_params = parse_query(levels,params)# fuzzy_matching,empty_value_matching,multi_value_matching)

    all_data = await request.state.query_service.query_instances(curated_params,limit,offset,study_uid,series_uid)

    temp = []

    for aa in all_data:
        temp.append(aa.to_dicom_json(request.state.server_base_url))

    response = JSONResponse(temp)#content=cc,media_type=media_type)
    return response
