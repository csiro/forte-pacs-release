from typing import Optional, Dict,Any, List
import asyncio
from collections import defaultdict
import requests
from datetime import datetime
from fhir.resources.imagingstudy import ImagingStudy
from fhir.resources.imagingstudy import ImagingStudySeries, ImagingStudySeriesInstance
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.bundle import Bundle
from fhir.resources.extension import Extension
from app.config import settings


headers = {
    'Content-Type': 'application/fhir+json',
    'Accept': 'application/fhir+json'
}

def extract_dicom_metadata(dicom_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract relevant metadata from DICOM JSON dictionaries.

        Args:
            dicom_dicts: List of DICOM data as dictionaries (JSON DICOM format)
                        with hex string tags (e.g., "00100020" for PatientID)

        Returns:
            Dictionary containing study-level and series-level metadata
        """
        if not dicom_dicts:
            raise ValueError("No DICOM dictionaries provided")

        # DICOM tag definitions as hex strings
        TAGS = {
            # Study level
            'StudyInstanceUID': '0020000D',
            'StudyID': '00200010',
            'StudyDate': '00080020',
            'StudyTime': '00080030',
            'StudyDescription': '00081030',
            'AccessionNumber': '00080050',
            # Patient level
            'PatientID': '00100020',
            'PatientName': '00100010',
            # Series level
            'SeriesInstanceUID': '0020000E',
            'SeriesNumber': '00200011',
            'SeriesDescription': '0008103E',
            'Modality': '00080060',
            'BodyPartExamined': '00180015',
            # Instance level
            'SOPInstanceUID': '00080018',
            'SOPClassUID': '00080016',
            'InstanceNumber': '00200013',
            'Rows': '00280010',
            'Columns': '00280011',
            'BitsAllocated': '00280100',
            'NumberOfFrames': '00280008'
        }

        def get_dicom_value(dicom_dict: Dict[str, Any], tag: str, default: str = '') -> str:
            """
            Extract value from DICOM JSON dictionary using hex tag.

            DICOM JSON format typically has structure:
            {
              "00100020": {
                "vr": "LO",
                "Value": ["PATIENT123"]
              }
            }
            """
            if tag not in dicom_dict:
                return default

            tag_data = dicom_dict[tag]

            # Handle different DICOM JSON structures
            if isinstance(tag_data, dict):
                # Standard DICOM JSON format
                if 'Value' in tag_data:
                    value = tag_data['Value']
                    # Value is typically a list
                    if isinstance(value, list) and len(value) > 0:
                        return str(value[0])
                    elif isinstance(value, str):
                        return value
                # Some implementations might use 'val' or lowercase
                elif 'value' in tag_data:
                    value = tag_data['value']
                    if isinstance(value, list) and len(value) > 0:
                        return str(value[0])
                    elif isinstance(value, str):
                        return value
            elif isinstance(tag_data, str):
                # Direct string value
                return tag_data

            return default

        # Read first dictionary to get study-level information
        first_dicom = dicom_dicts[0]

        study_metadata = {
            'study_instance_uid': get_dicom_value(first_dicom, TAGS['StudyInstanceUID']),
            'study_id': get_dicom_value(first_dicom, TAGS['StudyID']),
            'study_date': get_dicom_value(first_dicom, TAGS['StudyDate']),
            'study_time': get_dicom_value(first_dicom, TAGS['StudyTime']),
            'study_description': get_dicom_value(first_dicom, TAGS['StudyDescription']),
            'accession_number': get_dicom_value(first_dicom, TAGS['AccessionNumber']),
            'patient_id': get_dicom_value(first_dicom, TAGS['PatientID']),
            'patient_name': get_dicom_value(first_dicom, TAGS['PatientName']),
            'modality': get_dicom_value(first_dicom, TAGS['Modality']),
            'series': defaultdict(lambda: {
                'instances': [],
                'series_instance_uid': '',
                'modality': '',
                'series_number': '',
                'series_description': '',
                'body_part': ''
            })
        }

        # Validate required fields
        if not study_metadata['study_instance_uid']:
            raise ValueError("StudyInstanceUID is required but not found in DICOM data")

        if not study_metadata['patient_id']:
            raise ValueError("PatientID is required but not found in DICOM data")

        # Process all dictionaries to organize by series
        for dicom_dict in dicom_dicts:
            try:
                series_uid = get_dicom_value(dicom_dict, TAGS['SeriesInstanceUID'])

                if not series_uid:
                    print(f"Warning: SeriesInstanceUID not found in instance, skipping")
                    continue

                # Initialize series metadata if first instance
                if not study_metadata['series'][series_uid]['series_instance_uid']:
                    study_metadata['series'][series_uid].update({
                        'series_instance_uid': series_uid,
                        'modality': get_dicom_value(dicom_dict, TAGS['Modality']),
                        'series_number': get_dicom_value(dicom_dict, TAGS['SeriesNumber']),
                        'series_description': get_dicom_value(dicom_dict, TAGS['SeriesDescription']),
                        'body_part': get_dicom_value(dicom_dict, TAGS['BodyPartExamined'])
                    })

                # Add instance information
                sop_instance_uid = get_dicom_value(dicom_dict, TAGS['SOPInstanceUID'])
                sop_class_uid = get_dicom_value(dicom_dict, TAGS['SOPClassUID'])

                if sop_instance_uid and sop_class_uid:
                    study_metadata['series'][series_uid]['instances'].append({
                        'sop_instance_uid': sop_instance_uid,
                        'sop_class_uid': sop_class_uid,
                        'instance_number': get_dicom_value(dicom_dict, TAGS['InstanceNumber']),
                        'rows': get_dicom_value(dicom_dict, TAGS['Rows']),
                        'columns': get_dicom_value(dicom_dict, TAGS['Columns']),
                        'frames': get_dicom_value(dicom_dict, TAGS['NumberOfFrames'],'1'),
                        'bits_allocated': get_dicom_value(dicom_dict, TAGS['BitsAllocated']),
                    })
                else:
                    print(f"Warning: Missing SOPInstanceUID or SOPClassUID in instance")

            except Exception as e:
                print(f"Warning: Could not process DICOM dictionary: {e}")
                continue

        # Convert defaultdict to regular dict
        study_metadata['series'] = dict(study_metadata['series'])

        # Validate that we have at least one series with instances
        if not study_metadata['series'] or all(
            len(s['instances']) == 0 for s in study_metadata['series'].values()
        ):
            raise ValueError("No valid series with instances found in DICOM data")

        return study_metadata

def create_imaging_study_resource(metadata: Dict[str, Any]) -> ImagingStudy:
        """
        Create a FHIR R5 ImagingStudy resource from DICOM metadata.

        Args:
            metadata: DICOM metadata dictionary

        Returns:
            FHIR ImagingStudy resource
        """
        # Format study datetime
        study_datetime = None
        if metadata['study_date']:
            date_str = metadata['study_date']
            time_str = metadata.get('study_time', '000000')
            try:
                dt = datetime.strptime(f"{date_str}{time_str[:6]}", "%Y%m%d%H%M%S")
                study_datetime = dt.isoformat()
            except ValueError:
                pass

        # Create identifiers
        identifiers = [
            Identifier(
                system="urn:dicom:uid",
                value=metadata['study_instance_uid']
            )
        ]

        # Add accession number if available
        if metadata['accession_number']:
            identifiers.append(
                Identifier(
                    type=CodeableConcept(
                        coding=[
                            Coding(
                                system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                code="ACSN"
                            )
                        ]
                    ),
                    value=metadata['accession_number']
                )
            )

        # Create subject reference
        subject = Reference(
            identifier=Identifier(value=metadata['patient_id'])
        )

        # Collect modalities
        modalities = set()
        for series_data in metadata['series'].values():
            if series_data['modality']:
                modalities.add(series_data['modality'])

        modality_list = [
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://dicom.nema.org/resources/ontology/DCM",
                        code=mod
                    )
                ]
            ) for mod in modalities
        ] if modalities else None

        # Create series
        series_list = []
        for series_uid, series_data in metadata['series'].items():
            # Create instances for this series
            instances = []
            for instance in series_data['instances']:
                ## set the extensions
                
                print (instance)
                rows_extension = Extension(
                    url="https://forte.com/fhir/StructureDefinition/image-rows",
                    valueUnsignedInt=instance['rows']
                )
                columns_extension = Extension(
                    url="https://forte.com/fhir/StructureDefinition/image-columns",
                    valueUnsignedInt=instance['columns']
                )
                frames_extension = Extension(
                    url="https://forte.com/fhir/StructureDefinition/image-frames",
                    valueUnsignedInt=instance['frames']
                )
                bits_extension = Extension(
                    url="https://forte.com/fhir/StructureDefinition/image-bits-allocated",
                    valueUnsignedInt=instance['bits_allocated']
                )
                #image-rows named rows 0..1 MS and
                #image-columns named columns 0..1 MS and
                #image-frames named number_of_frames 0..1 MS and
                #image-bits-allocated named bits_allocated 0..1 MS
                instance_obj = ImagingStudySeriesInstance(
                    uid=instance['sop_instance_uid'],
                    sopClass=Coding(
                        system="urn:ietf:rfc:3986",
                        code=f"urn:oid:{instance['sop_class_uid']}"
                    ),
                    extension=[rows_extension,columns_extension,frames_extension,bits_extension]
                )

                if instance['instance_number'] and instance['instance_number'].isdigit():
                    instance_obj.number = int(instance['instance_number'])

                instances.append(instance_obj)

            # Create series object
            series_obj = ImagingStudySeries(
                uid=series_data['series_instance_uid'],
                modality=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://dicom.nema.org/resources/ontology/DCM",
                            code=series_data['modality']
                        )
                    ]
                ),
                numberOfInstances=len(instances),
                instance=instances if instances else None
            )

            if series_data['series_number'] and series_data['series_number'].isdigit():
                series_obj.number = int(series_data['series_number'])

            if series_data['series_description']:
                series_obj.description = series_data['series_description']

            if series_data['body_part']:
                series_obj.bodySite = CodeableReference( concept = CodeableConcept(
                    coding=[
                        Coding(display=series_data['body_part'])
                    ]
                    )
                )
            series_list.append(series_obj)

        # Calculate totals
        total_instances = sum(len(s.instance) if s.instance else 0 for s in series_list)

        # Create ImagingStudy resource
        imaging_study = ImagingStudy(
            status="available",
            identifier=identifiers,
            subject=subject,
            numberOfSeries=len(series_list),
            numberOfInstances=total_instances,
            series=series_list if series_list else None
        )

        # Add optional fields
        #if study_datetime:
        #    imaging_study.started = study_datetime

        if metadata['study_description']:
            imaging_study.description = metadata['study_description']

        if modality_list:
            imaging_study.modality = modality_list

        return imaging_study


def search_imaging_study(study_instance_uid: str) -> Optional[ImagingStudy]:
        """
        Search for an existing ImagingStudy resource by StudyInstanceUID.

        Args:
            study_instance_uid: DICOM Study Instance UID

        Returns:
            ImagingStudy resource if found, None otherwise
        """
        fhir_server_url =settings.FHIR_QUERY_SERVICE['FHIR_SERVER_URL']

        search_url = f"{fhir_server_url}/ImagingStudy"
        params = {
            'identifier': f"urn:dicom:uid|{study_instance_uid}"
        }

        try:
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()

            bundle = Bundle.parse_obj(response.json())

            # Check if any entries were returned
            if bundle.total and bundle.total > 0 and bundle.entry:
                return ImagingStudy.parse_obj(bundle.entry[0].resource.dict())

            return None

        except requests.exceptions.RequestException as e:
            print(f"Error searching for ImagingStudy: {e}")
            raise

def create_imaging_study(resource: ImagingStudy) -> ImagingStudy:
    """
    Create a new ImagingStudy resource on the FHIR server.

    Args:
        resource: FHIR ImagingStudy resource

    Returns:
        Created resource with server-assigned ID
    """
    fhir_server_url =settings.FHIR_QUERY_SERVICE['FHIR_SERVER_URL']
    create_url = f"{fhir_server_url}/ImagingStudy"

    try:
        response = requests.post(
            create_url,
            headers=headers,
            json=resource.dict(exclude_none=True)
        )
        response.raise_for_status()
        return ImagingStudy.parse_obj(response.json())

    except requests.exceptions.RequestException as e:
        print(f"Error creating ImagingStudy: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        raise
def update_meta_data_qido_fhir(params:List[Any])->None:
    """Update QIDO metadata synchronously.

    Args:
        params: Parameters for metadata update
    """
    asyncio.run(update_meta_data_qido_fhir_async(params))

async def update_meta_data_qido_fhir_async(params: List[Any]) -> None:
    """Update QIDO metadata asynchronously.

    Processes DICOM metadata and creates or updates study, series, and instance
    records in the SQL database for QIDO-RS query service support.

    Args:
        params: List containing metadata and pixel data for processing
    """



    # Sort all images by study
    all_meta = params[0]

    studies = {}
    for meta_data in all_meta:

        meta_json = meta_data

        study_instance_uid = meta_json["0020000D"]["Value"][0]

        if study_instance_uid not in studies:
            studies[study_instance_uid] = []

        studies[study_instance_uid].append(meta_data)


    for study_uid,study in studies.items():

        metadata = extract_dicom_metadata(study)

        study_uid = metadata['study_instance_uid']
        # Get the imaging study
        fhir_imaging_study = search_imaging_study(study_uid)
        imaging_study_resource = create_imaging_study_resource(metadata)

        if fhir_imaging_study:
            # Update the FHIR resource
            pass
        else:
            # Create a new FHIR resource
            result = create_imaging_study(imaging_study_resource)

