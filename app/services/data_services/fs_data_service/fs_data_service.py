'''
Implementation of the dataservice for a filesystem. This is used to store DICOM data in a filesystem.

Data is stored by converting the DICOM schema classes into JSON objects (via Pydantic v2)
and storing them in a directory structure.

'''

from typing import List
import os
from datetime import timedelta
from theine import Cache
from app.schema.dicom_instance import DCMInstance
from app.services.api.data_service import DataService



class FSDataService(DataService):
    """
       File system based implementation of the DICOM data service.

        This class implements the DataService interface using the filesystem to store data. 
    
    """
    def __init__(self,root_directory: str) -> None:
        '''
            Initialize the filesystem-based data service with a specified root directory.

            Args:
                root_directory (str): The base directory path where DICOM data will be stored and retrieved.
        '''
        self.root_directory=root_directory
        self.cache = Cache("tlfu",100)

    async def init_service(self) -> None:

        ## check that the filessystem exists and is accesible
        if not os.access(self.root_directory,os.F_OK):
            raise Exception(f"The configuired root directory {self.root_directory} of the \
                            data service does not exist or you do not have permissions to access it")

    ## TODO error checks on IO

    async def get_study(self, study_uid: str) -> List[DCMInstance]:
        """
            Retrieve all DICOM instances within a specific study.

            Args:
                study_uid (str): The unique identifier of the study.

            Returns:
                List[DCMInstance]: A list of all DICOM instances found in the specified study,
                including instances from all series within the study.
        """
        store_dir = os.path.join(self.root_directory,study_uid)

        temp = []

        for ser in os.listdir(store_dir):
            for ff in os.listdir(os.path.join(store_dir,ser)):
                temp_inst = self.cache.get((study_uid,ser,ff))

                if temp_inst is None:
                    with open(os.path.join(store_dir,ser,ff),'r', encoding="utf-8") as inst_file:
                        temp_inst = DCMInstance.model_validate_json(inst_file.read())
                        self.cache.set((study_uid,ser,ff),temp_inst,timedelta(seconds=300))
                temp.append(temp_inst)

        return temp


    ## TODO error checks on IO

    async def get_series(self,study_uid:str , series_uid: str)->List[DCMInstance]:
        """
            Retrieve all DICOM instances within a specific series of a study.

            Args:
                study_uid (str): The unique identifier of the study.
                series_uid (str): The unique identifier of the series within the study.

            Returns:
                List[DCMInstance]: A list of DICOM instances found in the specified series.
        """
        store_dir = os.path.join(self.root_directory,study_uid,series_uid)

        temp = []

        for ff in os.listdir(store_dir):
            temp_inst = self.cache.get((study_uid,series_uid,ff))

            if temp_inst is None:
                with open(os.path.join(store_dir,ff),'r', encoding="utf-8") as inst_file:
                    temp_inst = DCMInstance.model_validate_json(inst_file.read())
                    self.cache.set((study_uid,series_uid,ff),temp_inst,timedelta(seconds=300))

            temp.append(temp_inst)

        return temp


    ## TODO error checks on IO

    async def get_instance(self,study_uid : str , series_uid : str, instance_uid : str)->DCMInstance | None:
        """
            Retrieve a specific DICOM instance from a given study, series, and instance.

            Args:
                study_uid (str): The unique identifier of the study.
                series_uid (str): The unique identifier of the series within the study.
                instance_uid (str): The unique identifier of the specific instance.

            Returns:
                DCMInstance | None: The DICOM instance if found, otherwise None.
        """
        file = os.path.join(self.root_directory,study_uid,series_uid,instance_uid)

        if not os.access(file,os.F_OK):
            return None

        temp_inst = self.cache.get((study_uid,series_uid,instance_uid))
        if temp_inst is None:
            with open(file,'r', encoding="utf-8") as inst_file:
                temp_inst = DCMInstance.model_validate_json(inst_file.read())
                self.cache.set((study_uid,series_uid,instance_uid),temp_inst,timedelta(seconds=300))

        return temp_inst


    ## TODO error checks on IO

    async def store_instance(self,instance : DCMInstance) -> None:
        """
            Store a DICOM instance in the file system.

            Args:
                instance (DCMInstance): The DICOM instance to be stored.

            This method creates the necessary directory structure and saves the DICOM instance
            as a JSON file using its study, series, and instance UIDs for path construction.
        """
        store_dir = os.path.join(self.root_directory,instance.study_uid,instance.series_uid)
        store_file = os.path.join(store_dir,instance.instance_uid)
        if not os.access(store_dir,os.F_OK):
            os.makedirs(store_dir)

        with open(store_file,'w', encoding="utf-8") as inst_file:
            inst_file.write(instance.model_dump_json())

    async def dispose(self) -> None:
        """Dispose of anything on completion"""
