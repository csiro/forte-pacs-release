"""
Abstract API for all data services. A dataservice is responsible for storing and retrieving DICOM data.
DICOM data are represented as DCMInstance objects (see. app/schema/dicom_instance.py)
"""
from typing import List
from abc import ABC, abstractmethod
from app.schema.dicom_instance import DCMInstance

class DataService(ABC):
    """
    Abstract class /schema for data services. A dataservice is responsible for storing and retrieving DICOM data.
    """

    @abstractmethod
    async def init_service(self)->None:
        """Abstract method that should initialize the data service.
        """



    @abstractmethod
    async def get_study(self, study_uid: str) -> List[DCMInstance]:
        """ Abstract method that should return the DICOM instances for a given study uid
            in subclasses and an empty list if no instances are found for the study.

        Args:
            study_id (str): The study uid

        Returns:
            List[DCMInstance]: DICOM instances for the study.
        """
    @abstractmethod
    async def get_series(self, study_uid: str, series_uid: str) -> List[DCMInstance]:
        """Abstract method that should return the DICOM instances for a given series uid
        and an empty list if no instances are found for the series.

        Args:
            study_id (str): The study uid
            series_id (str): The series uid

        Returns:
            List[DCMInstance]: DICOM instances for the series.
        """
    @abstractmethod
    async def get_instance(self, study_uid: str, series_uid: str, instance_uid: str) \
            -> DCMInstance | None:
        """Abstract method that should return the DICOM instance for a given study,
        series and instance uid and None if no instance is found for the instance.

        Args:
            study_id (str): The study uid
            series_id (str): The series uid
            instance_id (str): The instance uid

        Returns:
            DCMInstance: DCMInstance corresponding to the dicom instance requested.
        """
    @abstractmethod
    async def store_instance(self,instance : DCMInstance) -> None:
        """ Abstrcat method that should store the given DICOM instance in the data service.

        Args:
            instance (DCMInstance): DCMInstance to store.
        """

    @abstractmethod
    async def dispose(self) -> None:
        """
            Abstract method that should dispose the data service.
        """
