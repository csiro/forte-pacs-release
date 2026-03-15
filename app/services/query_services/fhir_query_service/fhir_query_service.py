"""
This module contains the FHIR-based implementation of the DICOM query service.

This module provides FHIRQueryService which implements the QueryService interface
using FHIR search operations. It handles DICOM QIDO operations at study, series,
and instance levels with support for various DICOM query patterns.
"""

from operator import attrgetter
from typing import List, Dict, Any
import httpx
from app.schema.dicom_query import DICOMQueryStudy, DICOMQuerySeries, DICOMQueryInstance
from app.services.api.query_service import QueryService
from app.schema.query import MatchType,QueryLevel, QueryAttributeMatch
from app.services.query_services.fhir_query_service.utils import fhir_imaging_study_to_dicom_models

# DICOM attribute name to database field mapping
DICOM_ATTR_MAP = {}
DICOM_ATTR_MAP["StudyInstanceUID"]="identifier.where(system=urn:dicom:uid)" 
DICOM_ATTR_MAP["StudyDate"] = "started"  ## done
DICOM_ATTR_MAP["StudyTime"] = ""  ## TODO need to do
DICOM_ATTR_MAP["AccessionNumber"]="basedOn.identifier" 
DICOM_ATTR_MAP["ReferringPhysicianName"]="" ## TODO need to do
DICOM_ATTR_MAP["PatientName"]="patient.name"  ## TODO check
DICOM_ATTR_MAP["PatientID"]="patient.identifier" 
DICOM_ATTR_MAP["PatientBirthDate"]="patient.birthdate" 
DICOM_ATTR_MAP["PatientSex"]="patient.gender" ## done
DICOM_ATTR_MAP["StudyID"] = "" ## TODO
DICOM_ATTR_MAP["StudyDescription"] = "image-study-qido-study-description" ## done - from IG

DICOM_ATTR_MAP["Modality"] = "modality" ## done
DICOM_ATTR_MAP["SeriesInstanceUID"]= "series" ## done
DICOM_ATTR_MAP["SeriesDescription"] = "image-study-qido-series-description" ## done - from IG
DICOM_ATTR_MAP["SeriesNumber"] = "series_number" ## done - from IG
DICOM_ATTR_MAP["PerformedProcedureStepStartDate"]= "" ## TODO
DICOM_ATTR_MAP["PerformedProcedureStepStartTime"] = "" ## TODO

DICOM_ATTR_MAP["SOPClassUID"] = "dicom-class" ## done
DICOM_ATTR_MAP["SOPInstanceUID"] = "instance" ## done
DICOM_ATTR_MAP["InstanceNumber"] = "instance_number" ## done - from IG
DICOM_ATTR_MAP["Rows"] = "image-study-qido-rows" ## done - from IG
DICOM_ATTR_MAP["Columns"] = "image-study-qido-columns" ## done - from IG
DICOM_ATTR_MAP["NumberOfFrames"] = "image-study-qido-num-frames" ## done - from IG



def build_query_param(param:QueryAttributeMatch, fhir_search_variable : Dict,  mapped_fhir_search_attr:str)->None:
    """
    Build FHIR search query conditions based on DICOM query parameters.

    Converts DICOM query match types to appropriate FHIR search parameters.
    Supports single values, wildcards, lists, ranges, and empty value queries.

    Args:
        param: Query parameter with match_type and value.
        fhir_search_variable (Dict): Dictionary of FHIR search parameters to populate.
        mapped_fhir_search_attr (str): FHIR search parameter name.
    """
    if param.value is not None:
        if param.match_type == MatchType.single_value and isinstance(param.value,str):
            fhir_search_variable[mapped_fhir_search_attr]=param.value
        elif param.match_type == MatchType.wildcard and isinstance(param.value,str):
            val = param.value
            # .replace("?", "_")  # single character match is not supported by FHIR
            fhir_search_variable[mapped_fhir_search_attr]=val

        elif param.match_type == MatchType.list_of_uid and isinstance(param.value,List):

            fhir_search_variable[mapped_fhir_search_attr]=','.join(param.value)

        elif param.match_type == MatchType.range and isinstance(param.value,List):
            if param.value[0] is None:
                fhir_search_variable[mapped_fhir_search_attr]=f"ge{param.value}"

            elif param.value[1] is None:
                fhir_search_variable[mapped_fhir_search_attr]=f"le{param.value}"


    if param.match_type == MatchType.empty:
        fhir_search_variable[f"{mapped_fhir_search_attr}:missing"]="true"


def build_query_person_name(param:QueryAttributeMatch, fby_vars : Dict, f_vars:List, mapped_attr :str,
                            study_attr :Any)->None:
    """
    Build query conditions for DICOM Person Name attributes.

    Similar to build_query but specifically designed for handling Person Name
    data types which may have special formatting requirements.

    Args:
        param: Query parameter with match_type and value.
        fby_vars (Dict): Dictionary for filter_by conditions.
        f_vars (List): List for where clause conditions.
        mapped_attr (str): Database field name.
        study_attr: Attribute object for the field.
    """

    if param.match_type == MatchType.single_value and isinstance(param.value,str):
        fby_vars[mapped_attr]=param.value
    elif param.match_type == MatchType.wildcard and isinstance(param.value,str):
        val = param.value.replace("*","%").replace("?","_")
        f_vars.append(study_attr.like(val))
    elif param.match_type == MatchType.list_of_uid and isinstance(param.value,List):
        f_vars.append(study_attr.in_(param.value))
    elif param.match_type == MatchType.range and isinstance(param.value,List):
        if param.value[0] is None:
            f_vars.append(study_attr >= param.value[0])
        elif param.value[1] is None:
            f_vars.append(study_attr <= param.value[0])
    elif param.match_type == MatchType.empty :
        f_vars.append(study_attr == None)  # pylint: disable=singleton-comparison

def build_query(search_params):

    fhir_search_vars : Dict[str,str] = {}
    
    for param in search_params:

        mapped_fhir_search_attr = DICOM_ATTR_MAP[param.attr_name]

        if param.level == QueryLevel.study and mapped_fhir_search_attr != "modalities_in_study":
            pass

        elif mapped_fhir_search_attr == "modalities_in_study":
            if isinstance(param.value,List):
                fhir_search_vars["modality"] = ",".join(param.value)

            elif param.value is not None:
                fhir_search_vars["modality"] = param.value
            continue
        #else:
        #    continue

        build_query_param(param, fhir_search_vars, mapped_fhir_search_attr)
        
    return fhir_search_vars


class FHIRQueryService(QueryService):
    """
    FHIR-based implementation of the DICOM query service.

    This class implements the QueryService interface using FHIR search operations.
    It provides DICOM QIDO functionality for querying studies, series, and instances
    with support for various DICOM query patterns.
    """

    def __init__(self,fhir_server_url:str) ->None:
        """
        Initialize the FHIR query service.

        Args:
            fhir_server_url (str): Base URL of the FHIR server.
        """
        self.fhir_server_url = fhir_server_url


    async def init_service(self) -> None:
        """
        Initialize the FHIR query service.

        Sets up any required resources for FHIR search operations.
        """
        pass


    async def query_imaging_study(self, search_params : List[QueryAttributeMatch]):
        fhir_search_vars = build_query(search_params)

        studies = []
        series = []
        instances = []
        async with httpx.AsyncClient() as client:
            # Get all ImagingStudy resources

            response = await client.post(f"{self.fhir_server_url}/ImagingStudy/_search",params=fhir_search_vars)

            # Check response and convert to schema objects
            ## parse the response bundle
            resp_json = response.json()
            if resp_json["total"] != 0:
            
                for entry in resp_json["entry"]:
                    
                    if entry["resource"]["resourceType"] == "ImagingStudy":
                        (qstudy, qseries, qinstance) = fhir_imaging_study_to_dicom_models(entry["resource"])
                        studies.append(qstudy)
                        series.extend(qseries)
                        instances.extend(qinstance)

        return studies, series, instances


    async def create_dicom_study(self,all_meta:List[Dict[str,Dict]])->None:
        """
        Create a DICOM study entry in the database.

        Args:
            all_meta: Metadata for the DICOM study to be created.

        Note:
            This method is currently not implemented.
        """

    async def query_study(self,search_params : List[QueryAttributeMatch],limit:int,offset:int)->List[DICOMQueryStudy]:
        """
        Query DICOM studies based on search parameters.

        Performs a FHIR search for DICOM studies matching the provided search criteria.

        Args:
            search_params: List of query parameters with match types and values.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip for pagination.

        Returns:
            List[DICOMQueryStudy]: List of matching study objects.
        """

        studies, _ , _ = await self.query_imaging_study(search_params)

        

        return studies



    async def query_series(self,search_params:List[QueryAttributeMatch], limit :int,offset:int ,
                           study_uid:str | None =None)->List[DICOMQuerySeries]:
        """
        Query DICOM series based on search parameters.

        Performs a FHIR search for DICOM series matching the provided search criteria,
        optionally filtered by study UID.

        Args:
            search_params: List of query parameters with match types and values.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip for pagination.
            study_uid (str, optional): Study UID to filter series results.

        Returns:
            List[DICOMQuerySeries]: List of matching series objects.
        """

        if study_uid:
            search_params.append(QueryAttributeMatch(MatchType.single_value,QueryLevel.series,"StudyInstanceUID",study_uid))

        _ , series , _ = await self.query_imaging_study(search_params)

        return series

    async def query_instances(self, search_params : List[QueryAttributeMatch],limit:int,offset:int,
                              study_uid:str|None =None,series_uid:str| None=None)-> List[DICOMQueryInstance]:
        """
        Query DICOM instances based on search parameters.

        Performs a FHIR search for DICOM instances matching the provided search criteria,
        optionally filtered by study UID and/or series UID.

        Args:
            search_params: List of query parameters with match types and values.
            limit (int): Maximum number of results to return.
            offset (int): Number of results to skip for pagination.
            study_uid (str, optional): Study UID to filter instance results.
            series_uid (str, optional): Series UID to filter instance results.

        Returns:
            List[DICOMQueryInstance]: List of matching instance objects.
        """
        if study_uid:
            search_params.append(QueryAttributeMatch(MatchType.single_value,QueryLevel.instance,"StudyInstanceUID",study_uid))
        if series_uid:
            search_params.append(QueryAttributeMatch(MatchType.single_value,QueryLevel.instance,"SeriesInstanceUID",series_uid))


        _ , _ , instances = await self.query_imaging_study(search_params)



        return instances