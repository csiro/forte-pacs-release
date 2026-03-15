"""
This module contains the SQL-based implementation of the DICOM query service.

This module provides SQLQueryService which implements the QueryService interface
using SQLAlchemy for database operations. It handles DICOM QIDO operations
at study, series, and instance levels with support for various query patterns.
"""

from operator import attrgetter
from typing import List, Dict, Any
from sqlalchemy.sql.expression import and_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from app.services.query_services.sql_query_service.model import Base

from app.schema.dicom_query import DICOMQueryStudy, DICOMQuerySeries, DICOMQueryInstance
from app.services.api.query_service import QueryService
from app.schema.query import MatchType,QueryLevel, QueryAttributeMatch


from .model import DICOMQueryStudy as SQLDICOMStudy
from .model import DICOMQuerySeries as SQLDICOMSeries
from .model import DICOMQueryInstance as SQLDICOMInstance

# DICOM attribute name to database field mapping
DICOM_ATTR_MAP = {}
DICOM_ATTR_MAP["StudyInstanceUID"]="study_instance_uid"
DICOM_ATTR_MAP["StudyDate"] = "study_date"
DICOM_ATTR_MAP["StudyTime"] = "study_time"
DICOM_ATTR_MAP["AccessionNumber"]="accession_number"
DICOM_ATTR_MAP["ReferringPhysicianName"]="referring_physician_name"
DICOM_ATTR_MAP["PatientName"]="patient_name"
DICOM_ATTR_MAP["PatientID"]="patient_id"
DICOM_ATTR_MAP["PatientBirthDate"]="patient_birth_date"
DICOM_ATTR_MAP["PatientSex"]="patient_sex"
DICOM_ATTR_MAP["StudyID"] = "study_id"
DICOM_ATTR_MAP["StudyDescription"] = "study_description"
DICOM_ATTR_MAP["ModalitiesInStudy"]="modalities_in_study"


DICOM_ATTR_MAP["Modality"] = "modality"
DICOM_ATTR_MAP["SeriesInstanceUID"]= "series_instance_uid"
DICOM_ATTR_MAP["SeriesDescription"] = "series_description"
DICOM_ATTR_MAP["SeriesNumber"] = "series_number"
DICOM_ATTR_MAP["PerformedProcedureStepStartDate"]= "performed_procedure_step_start_date"
DICOM_ATTR_MAP["PerformedProcedureStepStartTime"] = "performed_procedure_step_start_time"

DICOM_ATTR_MAP["SOPClassUID"] = "sop_class_uid"
DICOM_ATTR_MAP["SOPInstanceUID"] = "sop_instance_uid"
DICOM_ATTR_MAP["InstanceNumber"] = "instance_number"



def build_query_param(param:QueryAttributeMatch, fby_vars : Dict, f_vars:List, mapped_attr:str,study_attr:Any)->None:
    """
        Build SQL query conditions based on DICOM query parameters.

        Converts DICOM query match types to appropriate SQLAlchemy filter conditions.
        Supports single values, wildcards, lists, ranges, and empty value queries.

        Args:
            param: Query parameter with match_type and value.
            fby_vars (Dict): Dictionary for filter_by conditions.
            f_vars (List): List for where clause conditions.
            mapped_attr (str): Database field name.
            study_attr: SQLAlchemy attribute for the field.
    """
    if param.value is not None:
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

    if param.match_type == MatchType.empty:
        f_vars.append(study_attr == None)  # pylint: disable=singleton-comparison


def build_query_person_name(param:QueryAttributeMatch, fby_vars : Dict, f_vars:List, mapped_attr :str,
                            study_attr :Any)->None:
    """
        Build SQL query conditions for DICOM Person Name attributes.

        Similar to build_query but specifically designed for handling Person Name
        data types which may have special formatting requirements.

        Args:
            param: Query parameter with match_type and value.
            fby_vars (Dict): Dictionary for filter_by conditions.
            f_vars (List): List for where clause conditions.
            mapped_attr (str): Database field name.
            study_attr: SQLAlchemy attribute for the field.
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



class SQLQueryService(QueryService):
    """
        SQL-based implementation of the DICOM query service.

        This class implements the QueryService interface using SQLAlchemy for database
        operations. It provides DICOM QIDO functionality for querying studies, series,
        and instances with support for various DICOM query patterns.
    """

    def __init__(self,sql_url:str) ->None:
        """
            Initialize the SQL query service.

            Args:
                sql_url (str): Database connection URL for SQLAlchemy.
        """
        self.sql_url = sql_url
        self.session_local : async_sessionmaker[AsyncSession]

    async def init_service(self) -> None:
        """
            Initialize the database service.

            Sets up the database engine, creates tables, and configures the session maker
            for async database operations.
        """

        engine = create_async_engine(
            self.sql_url
        )

        async def init_models() -> None:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

        await init_models()
        self.session_local = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Reference: https://fastapi.tiangolo.com/advanced/async-sql-databases/

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

            Performs a database query for DICOM studies matching the provided search criteria.

            Args:
                search_params: List of query parameters with match types and values.
                limit (int): Maximum number of results to return.
                offset (int): Number of results to skip for pagination.

            Returns:
                List[DICOMQueryStudy]: List of matching study objects.
        """

        async with self.session_local() as db_ses:
            # map the parameters to local model
            fby_vars : Dict[str,str] = {}
            f_vars : List[Any] = []
            for param in search_params:

                mapped_attr = DICOM_ATTR_MAP[param.attr_name]

                study_attr  = None
                if param.level == QueryLevel.study and mapped_attr != "modalities_in_study":

                    study_attr = getattr(SQLDICOMStudy,mapped_attr)

                elif mapped_attr == "modalities_in_study":
                    if isinstance(param.value,List):
                        f_vars.append(SQLDICOMStudy.series.any(SQLDICOMSeries.modality.in_(param.value)))
                    else:
                        f_vars.append(SQLDICOMStudy.series.any(SQLDICOMSeries.modality.in_([param.value])))

                    continue
                else:
                    continue

                build_query_param(param,fby_vars,f_vars,mapped_attr,study_attr)

            print (fby_vars)
            for ff in f_vars:
                print (ff)
            temp_q = select(SQLDICOMStudy).filter_by(**fby_vars).where(and_(*f_vars)).limit(limit).offset(offset)
            print (temp_q)
            res = (await db_ses.execute(temp_q)).unique().scalars().all()

            # Convert results to schema objects
            ret =  [await x.to_schema_obj() for x in res]

            return ret



    async def query_series(self,search_params:List[QueryAttributeMatch], limit :int,offset:int ,
                           study_uid:str | None =None)->List[DICOMQuerySeries]:
        """
            Query DICOM series based on search parameters.

            Performs a database query for DICOM series matching the provided search criteria,
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

        async with self.session_local() as db_ses:
            # map the parameters to local model
            fby_vars :Dict[str,str]= {}
            f_vars :List [Any]= []
            for param in search_params:

                mapped_attr = DICOM_ATTR_MAP[param.attr_name]

                study_attr  = None
                if param.level == QueryLevel.study:

                    if mapped_attr != "study_instance_uid":

                        temp = attrgetter('study.'+mapped_attr)
                        study_attr = temp(SQLDICOMSeries)
                    else:
                        study_attr = getattr(SQLDICOMSeries,mapped_attr)

                elif param.level == QueryLevel.series:
                    study_attr = getattr(SQLDICOMSeries,mapped_attr)
                else:
                    continue


                build_query_param(param,fby_vars,f_vars,mapped_attr,study_attr)

            temp_q = select(SQLDICOMSeries).filter_by(**fby_vars).where(and_(*f_vars)).limit(limit).offset(offset)

            res = (await db_ses.execute(temp_q)).unique().scalars().all()
            ret =  [await x.to_schema_obj() for x in res]

            return ret

    async def query_instances(self, search_params : List[QueryAttributeMatch],limit:int,offset:int,
                              study_uid:str|None =None,series_uid:str| None=None)-> List[DICOMQueryInstance]:
        """
            Query DICOM instances based on search parameters.

            Performs a database query for DICOM instances matching the provided search criteria,
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
        async with self.session_local() as db_ses:

            # map the parameters to local model
            fby_vars : Dict[str,str]= {}
            f_vars :List[Any]= []
            for param in search_params:

                mapped_attr = DICOM_ATTR_MAP[param.attr_name]

                study_attr  = None
                if param.level == QueryLevel.study:
                    temp = attrgetter('study.'+mapped_attr)
                    study_attr = temp(SQLDICOMInstance)

                elif param.level == QueryLevel.series:
                    temp = attrgetter('series.'+mapped_attr)
                    study_attr = temp(SQLDICOMInstance)

                else:
                    study_attr = getattr(SQLDICOMInstance,mapped_attr)

                build_query_param(param,fby_vars,f_vars,mapped_attr,study_attr)

            if study_uid:
                study_attr = getattr(SQLDICOMSeries,mapped_attr)
                fby_vars[mapped_attr]=study_uid

            temp_q = select(SQLDICOMInstance).filter_by(**fby_vars).where(and_(*f_vars)).limit(limit).offset(offset)

            res = (await db_ses.execute(temp_q)).unique().scalars().all()
            ret =  [x.to_schema_obj() for x in res]

            return ret

    async def dispose(self)->None:
        """Dispose of anything on completion"""
