'''
Abstract API for all query services. A query service is responsible for storing and querying selected metadata.
'''
from typing import List, Dict
from abc import ABC, abstractmethod
from app.schema.dicom_query import DICOMQueryStudy, DICOMQuerySeries, DICOMQueryInstance
from app.schema.query import MatchType,QueryLevel, QueryAttributeMatch


class QueryService(ABC):
    '''
    Abstract base class for a query service.
    '''
    @abstractmethod
    async def init_service(self) -> None:
        """ Abstract method to initialize the query service.
        """
        pass

    def supports_fuzzy_matching(self) -> bool:
        """Returns whether the query service supports fuzzy matching.

        Default is false. Override in subclasses.

        Returns:
            bool: False, indicating fuzzy matching is not supported by default.
        """
        return False

    @abstractmethod
    async def create_dicom_study(self,all_meta : List[Dict[str,Dict]]) -> None:
        """Creates a DICOM study based on the provided metadata.

        Args:
            all_meta (List[Dict[str,Dict]]): A list of dicom metadata objects represented as DICOM JSON.
        """


    @abstractmethod
    async def query_study(self,search_params : List[QueryAttributeMatch],limit: int,offset:int)->List[DICOMQueryStudy]:
            """
            An abstract method that should be implemented to query DICOM studies based on the provided search parameters.

            Args:
                search_params (List[QueryAttributeMatch]): Specifies the criteria for searching for DICOM studies. It could include
                    attributes such as patient name, study date, modality, etc. The function will use
                    these parameters to filter and retrieve the relevant DICOM studies from the database.
                limit (int): Represents the maximum number of results that should be returned by the query.
                    It specifies the limit on the number of DICOM studies that should be retrieved from
                    the database or system when the query is executed. This helps in controlling the
                    amount of data that is retrieved and processed by the query.
                offset (int): Represents the starting point from which the results should be retrieved.
                    It determines the number of initial results that should be skipped before fetching
                    the next set of results.

            Returns:
                List[DICOMQueryInstance] : A list of DICOMQueryStudy objects representing the queried DICOM studies.
            """


    @abstractmethod
    async def query_series(self,search_params : List[QueryAttributeMatch],limit : int,offset : int,study_uid : str | None = None )->List[DICOMQuerySeries]:
            """An abstract method that should be implemented to query DICOM series based on the provided search parameters.

            Args:
                search_params (List[QueryAttributeMatch]): Specifies the criteria for searching for DICOM studies. It could include
                    attributes such as patient name, study date, modality, etc. The function will use
                    these parameters to filter and retrieve the relevant DICOM studies from the database.
                limit (int): Represents the maximum number of results that should be returned by the query.
                    It specifies the limit on the number of DICOM studies that should be retrieved from
                    the database or system when the query is executed. This helps in controlling the
                    amount of data that is retrieved and processed by the query.
                offset (int): Represents the starting point from which the results should be retrieved.
                    It determines the number of initial results that should be skipped before fetching
                    the next set of results.
                study_uid (str): Study UID to which this query should be limited to.

            Returns:
                List[DICOMQueryInstance]: A list of DICOMQuerySeries objects representing the queried DICOM series.
            """
    @abstractmethod
    async def query_instances(self,search_params : List[QueryAttributeMatch],limit : int ,offset: int,study_uid : str | None = None,series_uid : str | None =None)->List[DICOMQueryInstance]:
            """
            An abstract method that should be implemented to query DICOM instances based on the provided search parameters.

            Args:
                search_params (List[QueryAttributeMatch]): Specifies the criteria for
                    searching for DICOM studies. It could include attributes such as patient name, study date,
                    modality, etc. The function will use these parameters to filter and retrieve the relevant DICOM
                    studies from the database.
                limit (int): Represents the maximum number
                    of results that should be returned by the query. It specifies the limit on the number of DICOM
                    studies that should be retrieved from the database or system when the query is executed. This
                    helps in controlling the amount of data that is retrieved and processed by the query.
                offset (int): Represents the
                    starting point from which the results should be retrieved. It determines the number of initial
                    results that should be skipped before fetching the next set of results.
                study_uid (str | None): Study UID to which this query should be limited to.
                series_uid (str | None): Series UID to which this query should be limited to.

            Returns:
                List[DICOMQueryInstance]: A list of DICOMQueryInstance objects representing the queried DICOM instances.
            """
