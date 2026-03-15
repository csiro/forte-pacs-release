from typing import List
from fastapi import HTTPException
from starlette.datastructures import MultiDict
from app.schema.query import QueryLevel, MatchType, QueryAttributeMatch


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
    "InstanceNumber":("00200013","IS",QueryLevel.instance),
    "Rows":("00280010","US",QueryLevel.instance),
    "Columns": ("00280011","US",QueryLevel.instance),
    "NumberOfFrames": ("00280008","US",QueryLevel.instance)
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
