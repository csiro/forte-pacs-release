"""
This module contains SQLAlchemy ORM models for DICOM query services.

This module defines the database models used for storing and querying DICOM metadata
including studies, series, and instances with their associated patient information.
"""

from datetime import date, time
from typing import Optional, List, Dict, Tuple
from sqlalchemy import  String, ForeignKey, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, composite
from sqlalchemy.ext.asyncio import AsyncAttrs
from app.schema.dicom_query import DICOMQueryStudy as SCHDICOMStudy
from app.schema.dicom_query import DICOMQuerySeries as SCHDICOMSeries
from app.schema.dicom_query import DICOMQueryInstance as SCHDICOMInstance

# declarative base class
class Base(AsyncAttrs, DeclarativeBase):
    """
        SQLAlchemy declarative base class with async attributes support.

        This base class provides async ORM capabilities for all DICOM query models.
    """


class DICOMPersonName(object):
    """
        Represents a DICOM Person Name data type.

        This class models the DICOM Person Name (PN) Value Representation,
        which stores structured name information including given name, family name,
        middle names, prefix, and suffix components.
    """

    def __init__(self, given_name:str, family_name:str, middle_names:str,prefix:str,suffix:str)->None:
        """
            Initialize a DICOM Person Name object.

            Args:
                given_name (str): The person's given name.
                family_name (str): The person's family name.
                middle_names (str): The person's middle names.
                prefix (str): Name prefix (e.g., Dr., Mr.).
                suffix (str): Name suffix (e.g., Jr., III).
        """
        self.given_name = given_name
        self.family_name = family_name
        self.middle_names = middle_names
        self.prefix = prefix
        self.suffix = suffix

    def __composite_values__(self)->Tuple[str,str,str,str,str]:
        return (self.given_name,self.family_name,self.middle_names,self.prefix,self.suffix)

    def __eq__(self,other:object)->bool:
        return isinstance(other,DICOMPersonName) and other.given_name == self.given_name \
                                                 and other.family_name == self.given_name \
                                                 and other.middle_names == self.middle_names

    def __ne__(self,other:object)->bool:
        return not self.__eq__(other)

    def to_dicom_string(self) -> str:
        """
            Convert the person name to DICOM string format.

            Converts the structured name components to the DICOM Person Name
            string format using caret (^) separators.

            Returns:
                str: DICOM formatted name string with components separated by carets.
        """
        temp = self.family_name+"^"+self.given_name+"^"+self.given_name+"^"+self.prefix+"^"+self.suffix
        # can trim trailing carets
        return temp



class DICOMQueryStudy(Base):
    """
        SQLAlchemy model representing a DICOM Study for query operations.

        This model stores study-level DICOM metadata including patient information,
        study details, and relationships to series and instances.
    """
    __tablename__ = "dicom_study"

    study_instance_uid : Mapped[str] = mapped_column(String, primary_key=True)
   # specific_character_set: Mapped[List[str]] = mapped_column(ARRAY(String)) ## use array
    specific_character_set: Mapped[str]
    study_date : Mapped[ date ]
    study_time : Mapped [ time ]
    accession_number : Mapped [str]

    rpn_given_name : Mapped[str] = mapped_column(String)
    rpn_family_name : Mapped[str]= mapped_column(String)
    rpn_middle_name : Mapped[str]= mapped_column(String)
    rpn_prefix : Mapped[str]= mapped_column(String)
    rpn_suffix : Mapped[str]= mapped_column(String)

    referring_physician_name : Mapped[DICOMPersonName]= composite(DICOMPersonName,rpn_given_name, \
                                                                  rpn_family_name,rpn_middle_name,rpn_prefix,rpn_suffix)

    timezone_offset_from_utc : Mapped[Optional[str]]

    pn_given_name : Mapped[str] = mapped_column(String)
    pn_family_name : Mapped[str]= mapped_column(String)
    pn_middle_name : Mapped[str]= mapped_column(String)
    pn_prefix : Mapped[str]= mapped_column(String)
    pn_suffix : Mapped[str]= mapped_column(String)
    patient_name : Mapped[DICOMPersonName]=composite(DICOMPersonName,pn_given_name,\
                                                     pn_family_name,pn_middle_name,pn_prefix,pn_suffix)

    patient_id : Mapped[str]
    patient_birth_date : Mapped [Optional[date]] = mapped_column(Date, default=None)
    patient_sex : Mapped[str]## enum
    study_id : Mapped[str] #s
    ## extra
    study_description : Mapped[str]


    series : Mapped[List["DICOMQuerySeries"]] = relationship(back_populates="study",lazy="joined")
    instances : Mapped[List["DICOMQueryInstance"]] = relationship(back_populates="study",\
                                                                  lazy="joined") ## may not need this

    async def to_schema_dict(self) -> Dict:
        """
            Convert the study model to a dictionary for schema validation.

            Transforms the SQLAlchemy model instance into a dictionary format
            suitable for creating schema objects, including calculated fields
            like modalities and instance counts.

            Returns:
                Dict: Dictionary representation of the study with additional computed fields.
        """
        temp = self.__dict__.copy()
        temp["modalities_in_study"]=[x.modality for x in await self.awaitable_attrs.series]
        temp["number_of_study_related_instances"] = len(await self.awaitable_attrs.instances)
        temp["number_of_study_related_series"] = len  (await self.awaitable_attrs.series)
        temp["patient_name"]= {"given_name":self.pn_given_name,"family_name":self.pn_family_name,\
                               "middle_names":[self.pn_middle_name],"prefix":self.pn_prefix,"suffix":self.pn_suffix}
        temp["referring_physician_name"]= {"given_name":self.rpn_given_name,"family_name":self.rpn_family_name,\
                                           "middle_names":[self.rpn_middle_name],"prefix":self.rpn_prefix,\
                                            "suffix":self.rpn_suffix}
        return temp

    async def to_schema_obj(self) -> SCHDICOMStudy:
        """
            Convert the study model to a schema object.

            Creates a validated SCHDICOMStudy schema object from the database model.

            Returns:
                SCHDICOMStudy: Validated schema object representing the study.
        """
        return SCHDICOMStudy.model_validate(await self.to_schema_dict())



class DICOMQuerySeries(Base):
    """
        SQLAlchemy model representing a DICOM Series for query operations.

        This model stores series-level DICOM metadata including modality information,
        procedure details, and relationships to studies and instances.
    """
    __tablename__ = "dicom_series"
    series_instance_uid: Mapped[str] = mapped_column(String, primary_key=True)
    modality : Mapped [str]  #s
    series_description: Mapped [Optional[str]]

    series_number : Mapped[str]#s
    performed_procedure_step_start_date: Mapped [Optional[date]]
    performed_procedure_step_start_time: Mapped [Optional[time]]

    scheduled_procedure_step_id : Mapped[Optional[str]]
    requested_procedure_id : Mapped[Optional[str]]

    study_instance_uid: Mapped[str] = mapped_column(ForeignKey("dicom_study.study_instance_uid"))
    study: Mapped ["DICOMQueryStudy"] = relationship(foreign_keys=[study_instance_uid],\
                                                     back_populates="series",lazy="joined")
    instances : Mapped[List["DICOMQueryInstance"]] = relationship(back_populates="series",lazy="joined")

    ## to generate
#    number_of_series_related_instances
#    retrieve_url

    async def to_schema_obj(self) -> SCHDICOMSeries:
        """
            Convert the series model to a schema object.

            Creates a validated SCHDICOMSeries schema object from the database model,
            including the related study information and instance count.

            Returns:
                SCHDICOMSeries: Validated schema object representing the series.
        """
        temp = self.__dict__.copy()
        temp["number_of_series_related_instances"] = len(self.instances)
        temp_study = await self.awaitable_attrs.study
        temp["study"] = await temp_study.to_schema_dict()
        return SCHDICOMSeries.model_validate(temp) ## CHECK



class DICOMQueryInstance(Base):
    """
        SQLAlchemy model representing a DICOM Instance for query operations.

        This model stores instance-level DICOM metadata including SOP information,
        image dimensions, and relationships to studies and series.
    """
    __tablename__ = "dicom_instance"

    sop_instance_uid : Mapped [str] = mapped_column(String, primary_key=True)

    #specific_character_set: Mapped[str]  ## might be different with different isntances
    sop_class_uid : Mapped [str]
    timezone_offset_from_utc : Mapped[Optional[str]]
    instance_number: Mapped [str]
    rows : Mapped[Optional[int]]
    columns : Mapped [Optional[int]]
    bits_allocated : Mapped[Optional[int]]
    number_of_frames : Mapped [Optional[int]]

    study_instance_uid: Mapped[str] = mapped_column(ForeignKey("dicom_study.study_instance_uid"))
    series_instance_uid: Mapped[str] = mapped_column(ForeignKey("dicom_series.series_instance_uid"))

    study: Mapped ["DICOMQueryStudy"] = relationship(foreign_keys=[study_instance_uid], \
                                                     back_populates="instances",lazy="joined")
    ## may not need this
    series : Mapped[List["DICOMQuerySeries"]] = relationship(foreign_keys=[series_instance_uid],\
                                                             back_populates="instances",lazy="joined")


    def to_schema_obj(self) -> SCHDICOMInstance:
        """
            Convert the instance model to a schema object.

            Creates a validated SCHDICOMInstance schema object from the database model.

            Returns:
                SCHDICOMInstance: Validated schema object representing the instance.

            Note:
                A cache could be implemented here for performance optimization.
        """
        return SCHDICOMInstance.model_validate(self.__dict__)
