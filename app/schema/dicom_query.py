"""
    Schema (pydantic) classes for  DICOM query (QIDO) functionality.
"""
from typing import List, Optional, Dict, Any
from datetime import date, time
from pydantic import BaseModel



class DICOMPersonName(BaseModel):
    """ This class represents a person's name in DICOM format.

    Attributes:
        given_names (Optional[List[str]]): Person's given names
        family_name (Optional[str]): Person's family name
        middle_name (Optional[str]): Person's middle name
        prefix (Optional[str]): Person's name prefix
        suffix (Optional[str]): Person's name suffix
    """

    given_names : Optional[List[str]]=None
    family_name : Optional[str]=None
    middle_name : Optional[str]=None
    prefix : Optional[str]=None
    suffix : Optional[str]=None

    def to_dicom_string(self) -> str:
        """
        The `to_dicom_string` method formats the patient name components into a DICOM-compliant string. The string includes the patient's family name, given names, middle name, prefix, and suffix, separated by caret (^) characters. If any of the name components are missing, empty strings are used in their place. The method also trims any trailing carets from the final string before returning it.

        Returns:
            str: A formatted DICOM patient name string.
        """

            ##
        fam_n = self.family_name if self.family_name else ""
        m_n = self.middle_name if self.middle_name else ""
        prefix = self.prefix if self.prefix else ""
        suffix = self.suffix if self.suffix else ""
        fir_n = " ".join(self.given_names) if self.given_names else ""

        temp = f"{fam_n}^{fir_n}^{m_n}^{prefix}^{suffix}"
        ## can trim trailling carets
        return temp



class DICOMQueryStudy(BaseModel):

    """ This class represents study level DICOM metadata for querying.

    Attributes:
        study_instance_uid  (str) : Study level unique identifier
        specific_character_set (str) : Specific character set
        study_date (date) : Study date
        study_time (time) : Study time
        accession_number (str) : Accession number
        modalities_in_study (List[str]) : List of modalities in study
        referring_physician_name (Optional[DICOMPersonName]) : Referring physician name
        timezone_offset_from_utc (Optional[str]) : Timezone offset from UTC
        patient_name (DICOMPersonName) : Patient name
        patient_id (str) : Patient ID
        patient_birth_date (date) : Patient birth date
        patient_sex (str) : Patient sex
        study_id (str) : Study ID
        study_description (str) : Study description
        number_of_study_related_instances (int) : Number of study related instances
        number_of_study_related_series (int) : Number of study related series
    """

    study_instance_uid : str
   # specific_character_set: Mapped[List[str]] = mapped_column(ARRAY(String)) ## use array
    specific_character_set: str
    study_date : date
    study_time : time
    accession_number : str
    modalities_in_study : List[str]
    referring_physician_name : Optional[DICOMPersonName]

    timezone_offset_from_utc : Optional[str]

    patient_name : DICOMPersonName

    patient_id : str
    patient_birth_date : Optional[date]
    patient_sex : str## enum
    study_id : str #s
    ## extra
    study_description : str
    number_of_study_related_instances : int
    number_of_study_related_series : int


    def to_dicom_json(self,server_url: str)-> Dict[str,Dict]:
        """
        Generates a DICOM JSON representation of the DICOMQueryStudy object.

        Args:
            server_url (str): The URL of the DICOM server.

        Returns:
            Dict[str, Dict]: A dictionary representing the DICOM JSON data, with DICOM tags as keys and their corresponding values as nested dictionaries.
        """
                ##
        temp: Dict[str,Dict[str,Any]] = {}
        temp["0020000D"] = {"vr":"UI","Value":[self.study_instance_uid]} ## study instance uid
        temp["00080005"] = {"vr": "CS", "Value": self.specific_character_set}
        temp["00080020"] = {"vr": "DA", "Value": [self.study_date.strftime("%Y%M%d")]}
        temp["00080030"] = {"vr": "TM", "Value": [self.study_time.strftime("%Y%M%d")]}
        temp["00080056"] = {"vr":"CS", "Value":["ONLINE"]}
        temp["00080050"] = {"vr": "SH", "Value":[self.accession_number]}
        temp["00080061"]={"vr":"CS", "Value": self.modalities_in_study}
        if self.referring_physician_name:
            temp["00080090"]={"vr": "PN", "Value":[{"Alphabetic" :self.referring_physician_name.to_dicom_string()}]}
        if self.timezone_offset_from_utc:
            temp["00080201"]={"vr":"SH", "Value":[self.timezone_offset_from_utc]}
        temp["00081190"]={"vr":"UR", "Value":[server_url+"/studies/"+self.study_instance_uid]}
        temp["00100010"]={"vr": "PN", "Value":[{"Alphabetic" :self.patient_name.to_dicom_string()}]}
        temp["00100020"]={"vr": "LO", "Value":[self.patient_id]}
        if self.patient_birth_date is not None:
            temp["00100030"]={"vr": "DA", "Value":[self.patient_birth_date.strftime("%Y%M%d")]} ##
        else:
            temp["00100030"]={"vr": "DA", "Value":[]}

        temp["00100040"]={"vr": "CS", "Value":[self.patient_sex]}
        temp["00200010"]={"vr": "SH" , "Value":[self.study_id]}
        temp["00201206"]={"vr": "IS", "Value":[self.number_of_study_related_series]}
        temp["00201208"]={"vr": "IS", "Value":[self.number_of_study_related_instances]}

        return temp

class DICOMQuerySeries(BaseModel):
    """ This class represents series level DICOM metadata for querying.

    Attributes:
        series_instance_uid (str) : Series level unique identifier
        modality (str) : Modality
        series_description (Optional[str]) : Series description
        series_number (str) : Series number
        performed_procedure_step_start_date (Optional[date]) : Performed procedure step start date
        performed_procedure_step_start_time (Optional[time]) : Performed procedure step start time
        scheduled_procedure_step_id (Optional[str]) : Scheduled procedure step ID
        requested_procedure_id (Optional[str]) : Requested procedure ID
        number_of_series_related_instances (int) : Number of series related instances
        study (DICOMQueryStudy) : Study object
    """

    series_instance_uid: str
    modality : str
    series_description: Optional[str]

    series_number : str
    performed_procedure_step_start_date: Optional[date]
    performed_procedure_step_start_time: Optional[time]

    scheduled_procedure_step_id : Optional[str]
    requested_procedure_id : Optional[str]

    number_of_series_related_instances: int
    study: DICOMQueryStudy

    def to_dicom_json(self,server_url : str ,study_level : bool = False) -> Dict[str,Dict]:
        """
        Generates a DICOM JSON representation of the DICOMQuerySeries object, including study-level attributes as specified.


        Args:
            server_url (str): The URL of the DICOM server.
            study_level (bool): If True, the DICOM JSON representation will also contain study level attributes, otherwise only series level attributes will be included.

        Returns:
            Dict[str, Dict]: A dictionary representing the DICOM JSON data, with DICOM tags as keys and their corresponding values as nested dictionaries.
        """


        temp = {}
        if study_level:
            temp=self.study.to_dicom_json(server_url)

        ## this will overwrite the study level common
        temp["00080005"] = {"vr": "CS", "Value": self.study.specific_character_set} ## check
        temp["00080060"]={"vr": "CS", "Value":[self.modality]}
        #if self.timezone_offset_from_utc: temp["00080201"]={"vr":"SH", "Value":[self.timezone_offset_from_utc]}
        if self.series_description: temp["0008103E"]={"vr": "LO", "Value":[self.series_description]}
        temp["00081190"]={"vr":"UR", "Value":[server_url+"/studies/"+self.study.study_instance_uid+"/series/"+self.series_instance_uid]}
        temp["0020000E"] = {"vr":"UI","Value":[self.series_instance_uid]} ## series instance uid
        temp["00200011"]={"vr": "IS", "Value":[self.series_number]}
        temp["00201209"]={"vr": "IS", "Value":[self.number_of_series_related_instances]}

        if self.performed_procedure_step_start_date: temp["00400244"]={"vr": "DA" , "Value":[self.performed_procedure_step_start_date.strftime("%Y%M%d")]}
        if self.performed_procedure_step_start_time: temp["00400245"]={"vr": "TM", "Value":[self.performed_procedure_step_start_time.strftime("%H%M%S")]}

        if self.scheduled_procedure_step_id and self.requested_procedure_id:
            spsid = {"vr":"SH", "Value":[self.scheduled_procedure_step_id]}
            rpid = {"vr":"SH", "Value":[self.requested_procedure_id]}

            temp["00400275"]={"vr": "SQ", "Value":[{"00400009":spsid, "00401001":rpid}]}

        return temp



class DICOMQueryInstance(BaseModel):
    """ This class represents instance level DICOM metadata for querying.

    Attributes:
        sop_instance_uid (str) : Instance level unique identifier
        sop_class_uid (str) : SOP class UID
        timezone_offset_from_utc (Optional[str]) : Timezone offset from UTC
        instance_number (int) : Instance number
        rows (Optional[int]) : Number of rows
        columns (Optional[int]) : Number of columns
        bits_allocated (Optional[int]) : Number of bits allocated
        number_of_frames (Optional[int]) : Number of frames
        study (DICOMQueryStudy) : Study object
        series (DICOMQuerySeries) : Series object
    """

    sop_instance_uid : str
    #specific_character_set: Mapped[str]  ## might be different with different isntances
    sop_class_uid : str
    timezone_offset_from_utc : Optional[str]
    instance_number: int
    rows : Optional[int]
    columns : Optional[int]
    bits_allocated : Optional[int]
    number_of_frames : Optional[int]
    study: DICOMQueryStudy
    series : DICOMQuerySeries



    def to_dicom_json(self,server_url : str,series_level : bool =False,study_level : bool =False) -> Dict[str,Dict]:
        """
            Generates a DICOM JSON representation of the DICOMQueryInstance object, including study and series-level attributes as specified.

        Args:
            server_url (str): The base URL of the DICOM server.
            series_level (bool): If True, the DICOM JSON representation will also contain series level attributes, otherwise only instance level attributes will be included.
            study_level (bool): If True, the DICOM JSON representation will also contain study level attributes, otherwise only series level attributes will be included.

        Returns:
            Dict[str, Dict]: A dictionary representing the DICOM JSON data, with DICOM tags as keys and their corresponding values as nested dictionaries.
        """
        temp = {}
        if series_level:
            temp=self.series.to_dicom_json(server_url,study_level)

        temp["00080016"]={"vr": "UI", "Value":[self.sop_class_uid]}
        temp["00080018"]={"vr": "UI", "Value":[self.sop_instance_uid]}
        temp["00080056"]={"vr": "CS", "Value":["ONLINE"]}
        if self.timezone_offset_from_utc: temp["00080201"]={"vr":"SH", "Value":[self.timezone_offset_from_utc]}
        temp["00081190"]={"vr":"UR", "Value":[server_url+"/studies/"+self.study.study_instance_uid+"/series/"+self.series.series_instance_uid+"/instances/"+self.sop_instance_uid]}
        temp["00200013"]={"vr": "IS", "Value":[self.instance_number]}
        if self.rows: temp["00280010"]={"vr": "IS", "Value":[self.rows]}
        if self.columns: temp["00280011"]={"vr": "IS", "Value":[self.columns]}
        if self.bits_allocated: temp["00280100"]={"vr": "IS", "Value":[self.bits_allocated]}
        if self.number_of_frames: temp["00280008"]={"vr": "IS", "Value":[self.number_of_frames]}

        return temp