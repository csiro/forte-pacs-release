"""DICOM QIDO metadata processing callbacks.

This module provides callback functions for processing DICOM metadata
and creating database entities for QIDO-RS query service support.
It handles the creation of study, series, and instance records from
DICOM metadata JSON for SQL-based query services. This is used by the qido 
service and rq task queue service.

"""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.services.query_services.sql_query_service.model import DICOMQueryInstance as SQLDCMInstance
from app.services.query_services.sql_query_service.model import DICOMQuerySeries as SQLDCMSeries
from app.services.query_services.sql_query_service.model import DICOMQueryStudy as SQLDCMStudy
from app.config import settings

def ton(meta_json : Dict[str,Any], tag: str) -> Any | None:
    """Extract tag value from DICOM metadata JSON, returning None if not found.

    Args:
        meta_json (dict): DICOM metadata in JSON format
        tag (str): DICOM tag to extract

    Returns:
        Any: The tag value if found, None otherwise
    """
    try:
        return meta_json[tag]["Value"][0]
    except KeyError:
        return None


def create_person_name(person_name_string : str|Dict[str,str], db_name_prefix:str)-> Dict[str,str]:
    """Create person name components from DICOM person name string.

    Parses a DICOM person name string into individual name components
    (family, given, middle, prefix, suffix) with the specified database
    field prefix.

    Args:
        person_name_string (str or dict): DICOM person name string or dict
        db_name_prefix (str): Database field prefix for name components

    Returns:
        dict: Dictionary with name component fields
    """
    sp = ["","","","",""]
    if isinstance(person_name_string, str):

        if person_name_string != "" and "^" in person_name_string:
            sp = person_name_string.split("^")
            ## TODO check all 5 components are present
    elif isinstance(person_name_string, dict):
        sp = person_name_string['Alphabetic'].split("^")  # hacky

    name_comp = lambda l,i : l[i] if i < len(l) else ""  # pylint disable=unnecessary-lambda
    temp = {}
    temp[db_name_prefix+"family_name"] = name_comp(sp,0)
    temp[db_name_prefix+"given_name"] = name_comp(sp,1)
    temp[db_name_prefix+"middle_name"] = name_comp(sp,2)
    temp[db_name_prefix+"prefix"] = name_comp(sp,3)
    temp[db_name_prefix+"suffix"] = name_comp(sp,4)

    return temp

def create_study(meta_json:Dict[str,Any])-> SQLDCMStudy:
    """Create a SQL study entity from DICOM metadata.

    Args:
        meta_json (dict): DICOM metadata in JSON format

    Returns:
        SQLDCMStudy: SQL study entity with populated fields
    """
    kwargs = {}
    kwargs["study_instance_uid"] = meta_json["0020000D"]["Value"][0]
    if "00080005" in meta_json.keys():
        kwargs["specific_character_set"] = meta_json["00080005"]["Value"][0]
    else:
        kwargs["specific_character_set"] = "ISO-IR 6"
    kwargs["study_date"] = datetime.strptime(meta_json["00080020"]["Value"][0],"%Y%m%d")
    study_time = meta_json["00080030"]["Value"][0]
    if '.' in study_time:
        study_time = study_time.split('.')[0]
    kwargs["study_time"] = datetime.strptime(study_time,"%H%M%S").time()
    kwargs["accession_number"] = ton(meta_json,"00080050")
    kwargs["timezone_offset_from_utc"] = ton(meta_json,"00080201")
    kwargs["patient_id"] = ton(meta_json,"00100020")
    if "00100030" in meta_json.keys() and "Value" in meta_json["00100030"].keys():
        kwargs["patient_birth_date"] = datetime.strptime(meta_json["00100030"]["Value"][0],"%Y%m%d")

    kwargs["patient_sex"] = ton (meta_json,"00100040")
    kwargs["study_id"] = ton (meta_json, "00200010")
    kwargs["study_description"] = ton(meta_json,"00081030") #

    patient_name = ton(meta_json,"00100010")
    if patient_name:
        kwargs.update(create_person_name(patient_name,"pn_"))
    else:
        kwargs.update(create_person_name("","pn_"))

    rpn = ton(meta_json,"00080090")
    if rpn:
        kwargs.update(create_person_name(rpn,"rpn_"))
    else:
        kwargs.update(create_person_name("","rpn_"))
    return SQLDCMStudy(**kwargs)

def create_series(meta_json: Dict[str,Any], study:SQLDCMStudy) -> SQLDCMSeries:
    """Create a SQL series entity from DICOM metadata.

    Args:
        meta_json (dict): DICOM metadata in JSON format
        study (SQLDCMStudy): Parent study entity

    Returns:
        SQLDCMSeries: SQL series entity with populated fields
    """
    kwargs = {}

    kwargs["modality"] = meta_json["00080060"]["Value"][0]
    kwargs["series_instance_uid"] = meta_json["0020000E"]["Value"][0]
    kwargs["series_description"] = ton(meta_json,"0008103E")
    kwargs["series_number"] = str(ton(meta_json,"00200011"))
    if "00400244" in meta_json.keys():
        kwargs["performed_procedure_step_start_date"] = datetime.strptime(meta_json["00400244"]["Value"][0],"%Y%m%d")
    if "00400245" in meta_json.keys():
        pps_start = meta_json["00400245"]["Value"][0]
        if '.' in pps_start:
            pps_start = pps_start.split('.')[0]

        kwargs["performed_procedure_step_start_time"] = datetime.strptime(pps_start,"%H%M%S").time()
    if "00400275" in meta_json.keys():
        kwargs["scheduled_procedure_step_id"] = ton(meta_json["00400275"]["Value"][0],"00400009")
        kwargs["requested_procedure_id"] = ton(meta_json["00400275"]["Value"][0],"00401001")

    kwargs["study"] = study
    return SQLDCMSeries(**kwargs)

def create_instance(meta_json : Dict[str,Any], study : SQLDCMStudy,
                    series : SQLDCMSeries)-> SQLDCMInstance:
    """Create a SQL instance entity from DICOM metadata.

    Args:
        meta_json (dict): DICOM metadata in JSON format
        pixel_data: Pixel data information
        study (SQLDCMStudy): Parent study entity
        series (SQLDCMSeries): Parent series entity

    Returns:
        SQLDCMInstance: SQL instance entity with populated fields
    """
    kwargs = {}
    kwargs["sop_instance_uid"] = meta_json["00080018"]["Value"][0]
    #kwargs["specific_character_set"] = meta_json[""]["Value"][0]
    kwargs["sop_class_uid"] = meta_json["00080016"]["Value"][0]
    kwargs["timezone_offset_from_utc"] = ton(meta_json,"00080201")
    kwargs["instance_number"] = str(ton(meta_json,"00200013"))
    kwargs["rows"] = meta_json["00280010"]["Value"][0]
    kwargs["columns"] = meta_json["00280011"]["Value"][0]
    kwargs["bits_allocated"] = meta_json["00280100"]["Value"][0]
    kwargs["number_of_frames"] = ton(meta_json,"00280008")
    kwargs["study"] = study
    kwargs["series"] = series
    return SQLDCMInstance(**kwargs)


def update_meta_data_qido(params:List[Any])->None:
    """Update QIDO metadata synchronously.

    Args:
        params: Parameters for metadata update
    """
    asyncio.run(update_meta_data_qido_async(params))


async def update_meta_data_qido_async(params: List[Any]) -> None:
    """Update QIDO metadata asynchronously.

    Processes DICOM metadata and creates or updates study, series, and instance
    records in the SQL database for QIDO-RS query service support.

    Args:
        params: List containing metadata and pixel data for processing
    """





    sql_url = None
    username = None
    password =  None
    sql_dialect = None

    try:
        sql_dialect=settings.SQL_QUERY_SERVICE['sql_dialect']
    except KeyError as e:
        raise Exception("Dialect required for sql query service is missing.") from e

    try:
        sql_url = settings.SQL_QUERY_SERVICE['sql_url']
    except KeyError as e:
        raise Exception("URL required for query service is missing.") from e

    try:
        username = settings.SQL_QUERY_SERVICE['sql_username']
    except KeyError as e:
        ## log it.
        pass
    try:
        password = settings.SQL_QUERY_SERVICE['sql_password']
    except KeyError as e:
        pass
    username_str = ""
    if username:
        username_str=username_str+username
        if password:
            username_str+=":"+password

    if username_str != "":
        sql_url_full = sql_dialect+"://"+username_str+"@"+sql_url
    else:
        sql_url_full = sql_dialect+"://"+sql_url



    engine = create_async_engine(
        sql_url_full
    )

    session_local = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async with session_local() as db_ses:
        ## check for person name

        all_meta = params[0]


        for meta_data in all_meta:

            meta_json = meta_data
            #meta_json = json.loads(meta_data[0])
            instance_uid = meta_json["00080018"]["Value"][0]
            study_instance_uid = meta_json["0020000D"]["Value"][0]
            series_instance_uid = meta_json["0020000E"]["Value"][0]
            ## check if istance
            db_ses = session_local()


            instance  = (await db_ses.execute(select(SQLDCMInstance).filter_by(sop_instance_uid=instance_uid))).scalars().first()  # pylint: disable=line-too-long
            series  = (await db_ses.execute(select(SQLDCMSeries).filter_by(series_instance_uid=series_instance_uid))).scalars().first() # pylint: disable=line-too-long
            study  = (await db_ses.execute(select(SQLDCMStudy).filter_by(study_instance_uid=study_instance_uid))).scalars().first() # pylint: disable=line-too-long
            await db_ses.commit()


            if instance is not None: # already have seen this instance so do nothing
                return

            if study is None:
                study = create_study(meta_json)
             #   series = create_series(meta_json,study)
                db_ses.add(study)
                #db_ses.commit()

            if series is None:
                series = create_series(meta_json,study)
                db_ses.add(series)
                #db_ses.commit()

            instance = create_instance(meta_json, study, series)

            db_ses.add(instance)
            await db_ses.commit()
