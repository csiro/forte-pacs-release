"""
    This module contains the sop storage classes 
"""

from pydicom.uid import *

# https://dicom.nema.org/medical/Dicom/current/output/chtml/part03/chapter_A.html
# https://dicom.nema.org/medical/dicom/current/output/html/part04.html#sect_B.5.1.20

# Read dicom encaps
# https://github.com/pydicom/pydicom/blob/master/pydicom/encaps.py

IMAGE = [ComputedRadiographyImageStorage, DigitalXRayImageStorageForPresentation, DigitalXRayImageStorageForProcessing,
         DigitalMammographyXRayImageStorageForPresentation, DigitalMammographyXRayImageStorageForProcessing,
         DigitalIntraOralXRayImageStorageForPresentation, DigitalIntraOralXRayImageStorageForProcessing ,
         EnhancedXAImageStorage  , EnhancedXRFImageStorage , PositronEmissionTomographyImageStorage ,
         LegacyConvertedEnhancedPETImageStorage , XRay3DAngiographicImageStorage , XRay3DCraniofacialImageStorage ,
         BreastTomosynthesisImageStorage , BreastProjectionXRayImageStorageForPresentation ,
         BreastProjectionXRayImageStorageForProcessing , EnhancedPETImageStorage ,
         IntravascularOpticalCoherenceTomographyImageStorageForPresentation ,
         IntravascularOpticalCoherenceTomographyImageStorageForProcessing , CTImageStorage , EnhancedCTImageStorage ,
         LegacyConvertedEnhancedCTImageStorage  , MRImageStorage , EnhancedMRImageStorage , EnhancedMRColorImageStorage,
         LegacyConvertedEnhancedMRImageStorage , DICOSCTImageStorage , DICOSDigitalXRayImageStorageForPresentation ,
         DICOSDigitalXRayImageStorageForProcessing , UltrasoundImageStorage , SecondaryCaptureImageStorage ,
         VLEndoscopicImageStorage ,  VLMicroscopicImageStorage  , VLSlideCoordinatesMicroscopicImageStorage ,
         VLPhotographicImageStorage   , StereometricRelationshipStorage , OphthalmicTomographyImageStorage  ,
         OphthalmicOpticalCoherenceTomographyEnFaceImageStorage ,
         OphthalmicOpticalCoherenceTomographyBscanVolumeAnalysisStorage ,
         VLWholeSlideMicroscopyImageStorage , DermoscopicPhotographyImageStorage , CornealTopographyMapStorage ,
         OphthalmicThicknessMapStorage , ParametricMapStorage , SegmentationStorage , EnhancedUSVolumeStorage]

PROTOCOLS_SOP_CLASSES = [CTDefinedProcedureProtocolStorage,CTPerformedProcedureProtocolStorage, ProtocolApprovalStorage,
                         XADefinedProcedureProtocolStorage,XAPerformedProcedureProtocolStorage]
ENCAPSULATED_DOCUMENT_SOP_CLASSES = [EncapsulatedPDFStorage,EncapsulatedCDAStorage,EncapsulatedSTLStorage,
                                     EncapsulatedOBJStorage,EncapsulatedMTLStorage]
SR_DOCUMENT_SOP_CLASSES = [BasicTextSRStorage,EnhancedSRStorage,ComprehensiveSRStorage,Comprehensive3DSRStorage,
                           ExtensibleSRStorage,MammographyCADSRStorage,ProcedureLogStorage,
                           KeyObjectSelectionDocumentStorage,ChestCADSRStorage,XRayRadiationDoseSRStorage,
                           RadiopharmaceuticalRadiationDoseSRStorage,ColonCADSRStorage,ImplantationPlanSRStorage,
                           AcquisitionContextSRStorage,SimplifiedAdultEchoSRStorage,PatientRadiationDoseSRStorage,
                           PlannedImagingAgentAdministrationSRStorage,PerformedImagingAgentAdministrationSRStorage,
                           EnhancedXRayRadiationDoseSRStorage,MacularGridThicknessAndVolumeReportStorage,
                           SpectaclePrescriptionReportStorage,VolumeRenderingVolumetricPresentationStateStorage]
WAVEFORM_SOP_CLASSES = [TwelveLeadECGWaveformStorage,GeneralECGWaveformStorage,AmbulatoryECGWaveformStorage,
                        HemodynamicWaveformStorage,CardiacElectrophysiologyWaveformStorage,
                        BasicVoiceAudioWaveformStorage,GeneralAudioWaveformStorage,ArterialPulseWaveformStorage,
                        RespiratoryWaveformStorage,MultichannelRespiratoryWaveformStorage,
                        RoutineScalpElectroencephalogramWaveformStorage,ElectromyogramWaveformStorage,
                        ElectrooculogramWaveformStorage,SleepElectroencephalogramWaveformStorage,
                        BodyPositionWaveformStorage]



MULTIFRAME_IMAGE_SOP_CLASSES=[NuclearMedicineImageStorage,
                              UltrasoundMultiFrameImageStorage,
                              MultiFrameSingleBitSecondaryCaptureImageStorage,
                              MultiFrameGrayscaleByteSecondaryCaptureImageStorage,
                              MultiFrameGrayscaleWordSecondaryCaptureImageStorage,
                              MultiFrameTrueColorSecondaryCaptureImageStorage,
                              OphthalmicPhotography8BitImageStorage,
                              OphthalmicPhotography16BitImageStorage,
                              WideFieldOphthalmicPhotographyStereographicProjectionImageStorage,
                              WideFieldOphthalmicPhotography3DCoordinatesImageStorage,
                              XRayAngiographicImageStorage,
                              XRayRadiofluoroscopicImageStorage]

VIDEO_SOP_CLASSES = [VideoEndoscopicImageStorage, VideoMicroscopicImageStorage, VideoPhotographicImageStorage ]

PRESENTATION_SOP_CLASSES = [GrayscaleSoftcopyPresentationStateStorage,
                            SegmentedVolumeRenderingVolumetricPresentationStateStorage,
                            MultipleVolumeRenderingVolumetricPresentationStateStorage,
                            ColorSoftcopyPresentationStateStorage,
                            PseudoColorSoftcopyPresentationStateStorage,
                            BlendingSoftcopyPresentationStateStorage,
                            XAXRFGrayscaleSoftcopyPresentationStateStorage,
                            GrayscalePlanarMPRVolumetricPresentationStateStorage,
                            AdvancedBlendingPresentationStateStorage]

RT_IMAGE_SOP_CLASSES = [RTDoseStorage, RTImageStorage] ## conditinal multi-frame
RT_NONIMAGE_SOP_CLASSES = [RTStructureSetStorage,RTBeamsTreatmentRecordStorage,RTPlanStorage,
                           RTBrachyTreatmentRecordStorage,RTTreatmentSummaryRecordStorage,
                           RTIonPlanStorage,RTIonBeamsTreatmentRecordStorage]

## missing Enhanced RT Image Storage, Enhanced Continuous RT Image Storage
RT_GEN2_IMAGE_SOP_CLASSES = [EnhancedRTImageStorage,EnhancedContinuousRTImageStorage]
## missing RT Patient Position Acquisition Instruction Storage
RT_GEN2_NONIMAGE_SOP_CLASSES =[RTPhysicianIntentStorage,RTSegmentAnnotationStorage,RTRadiationSetStorage,
                               RTRadiationSalvageRecordStorage,RTRadiationRecordSetStorage,
                               RTRadiationSetDeliveryInstructionStorage,RTTreatmentPreparationStorage,
                               RTBrachyApplicationSetupDeliveryInstructionStorage,RTBeamsDeliveryInstructionStorage,
                               CArmPhotonElectronRadiationStorage,RoboticArmRadiationStorage,
                               CArmPhotonElectronRadiationRecordStorage,TomotherapeuticRadiationRecordStorage,
                               TomotherapeuticRadiationStorage,RoboticRadiationRecordStorage,
                               CompositingPlanarMPRVolumetricPresentationStateStorage]


NON_IMAGE_SOP_CLASSES = [ContentAssessmentResultsStorage, MicroscopyBulkSimpleAnnotationsStorage,
                         OphthalmicVisualFieldStaticPerimetryMeasurementsStorage, MRSpectroscopyStorage,
                         RawDataStorage, LensometryMeasurementsStorage, AutorefractionMeasurementsStorage,
                         KeratometryMeasurementsStorage, SubjectiveRefractionMeasurementsStorage,
                         VisualAcuityMeasurementsStorage, OphthalmicAxialMeasurementsStorage,
                         IntraocularLensCalculationsStorage, SpatialRegistrationStorage,
                         DeformableSpatialRegistrationStorage, SpatialFiducialsStorage,
                         SurfaceSegmentationStorage, TractographyResultsStorage, SurfaceScanMeshStorage,
                         SurfaceScanPointCloudStorage, RealWorldValueMappingStorage,BasicStructuredDisplayStorage]

ALL_IMAGE_SOP_CLASSES = IMAGE+MULTIFRAME_IMAGE_SOP_CLASSES+RT_IMAGE_SOP_CLASSES+RT_GEN2_IMAGE_SOP_CLASSES
RENDERABLE_IMAGE_SOP_CLASSES=IMAGE+MULTIFRAME_IMAGE_SOP_CLASSES
ALL_SOP_CLASSES = IMAGE+PROTOCOLS_SOP_CLASSES+ENCAPSULATED_DOCUMENT_SOP_CLASSES+SR_DOCUMENT_SOP_CLASSES+\
                  WAVEFORM_SOP_CLASSES+MULTIFRAME_IMAGE_SOP_CLASSES+VIDEO_SOP_CLASSES+PRESENTATION_SOP_CLASSES+\
                  RT_IMAGE_SOP_CLASSES+RT_NONIMAGE_SOP_CLASSES+RT_GEN2_IMAGE_SOP_CLASSES+\
                  RT_GEN2_NONIMAGE_SOP_CLASSES+NON_IMAGE_SOP_CLASSES

## get the reource types.

def is_presentation_state_storage(sop_class_uid: str) -> bool:
    """
        Checks whether sop_class_uid is for a presentation state storage class

        Args:
            sop_class_uid (str): DICOM sop class UID.

        Returns:
            bool: True if sop_class_uid is presentation state storage class.

    """
    if sop_class_uid in PRESENTATION_SOP_CLASSES:
        return True
    return False

def is_supported_stow_sop_class(sop_class_uid: str)-> bool:
    """
        Checks whether sop_class_uid is supported for STOW

        Args:
            sop_class_uid (str): DICOM sop class UID.

        Returns:
            bool: True if sop_class_uid is supported for STOW.

    """
    if sop_class_uid in ALL_SOP_CLASSES:
        return True
    return False



def is_encapsulated_document_class(sop_class_uid: str)->bool:
    """
        Checks whether sop_class_uid is for an encapsulated document class

        Args:
            sop_class_uid (str): DICOM sop class UID.

        Returns:
            bool: True if sop_class_uid is for an encapsulated storage class.

    """

    if sop_class_uid in ENCAPSULATED_DOCUMENT_SOP_CLASSES:
        return True
    return False

def is_image_sop_class(sop_class_uid:str)-> bool:
    """
        Checks whether sop_class_uid is for an image class

        Args:
            sop_class_uid (str): DICOM sop class UID.

        Returns:
            bool: True if sop_class_uid is for an image class.

    """
    if sop_class_uid in ALL_IMAGE_SOP_CLASSES:
        return True
    return False

def is_renderable_image_sop_class(sop_class_uid:str)->bool:
    """
        Checks whether sop_class_uid is for a renderable class

        Args:
            sop_class_uid (str): DICOM sop class UID.

        Returns:
            bool: True if sop_class_uid is for a renderable class.

    """
    if sop_class_uid in RENDERABLE_IMAGE_SOP_CLASSES:
        return True
    return False



def is_supported_stow_transfer_syntax(transfer_syntax_uid: str) -> bool:
    """
        Checks whether transfer_syntax_uid is for a supported transfer syntax 
        for STOW. 
        Currently all transfer syntaxes are supported for STOW but these may
        become configurable in the future.

        Args:
            transfer_syntax_uid (str): DICOM transfer_syntax UID.

        Returns:
            bool: True if transfer syntax uid is for a supported transfer syntax.
        
    """

    return True

def is_compressed_transfer_syntax(transfer_syntax_uid: str | None) -> bool:
    """
        Checks whether transfer_syntax_uid is for a compressed type.

        Args:
            transfer_syntax_uid (str): DICOM transfer_syntax UID.

        Returns:
            bool: True if transfer syntax uid is for a compressed transfer syntax.
        
    """
    if transfer_syntax_uid == ExplicitVRLittleEndian:
        return False
    return True


def is_supported_transfer_syntax(sop_class_uid: str, transfer_syntax_uid: str) -> bool:
    """
        Checks whether transfer_syntax_uid is for a supported transfer syntax. 
        Currently all transfer syntaxes are supported but these may
        become configurable in the future.

        Args:
            transfer_syntax_uid (str): DICOM transfer_syntax UID.

        Returns:
            bool: True if transfer syntax uid is for a supported transfer syntax.
        
    """
    return True
