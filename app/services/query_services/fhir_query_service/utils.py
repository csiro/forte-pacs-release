"""
    Conversion functions from FHIR R5/R6 ImagingStudy resource to
    DICOMQueryStudy, DICOMQuerySeries, and DICOMQueryInstance.

    FHIR ImagingStudy reference:
        https://www.hl7.org/fhir/imagingstudy.html  (R5/R6)

    Notes
    -----
    * A FHIR ImagingStudy maps directly to one DICOMQueryStudy.
    * Each ImagingStudy.series element maps to one DICOMQuerySeries.
    * Each ImagingStudy.series.instance element maps to one DICOMQueryInstance.
    * Many DICOM attributes are optional in FHIR; sensible defaults / None
      values are used where data is absent.
    * FHIR dates/times are ISO-8601 strings; they are parsed to Python
      date / time objects as required by the Pydantic models.
"""

from __future__ import annotations

from datetime import date, time, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.schema.dicom_query import (
    DICOMPersonName,
    DICOMQueryInstance,
    DICOMQuerySeries,
    DICOMQueryStudy,
)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO-8601 date string (YYYY-MM-DD) to a ``date`` object."""
    if not value:
        return None
    # FHIR dates may be partial (YYYY or YYYY-MM); pad to a full date
    parts = value[:10].split("-")
    if len(parts) == 1:
        return date(int(parts[0]), 1, 1)
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    return date.fromisoformat(value[:10])


def _parse_time(value: Optional[str]) -> Optional[time]:
    """
    Parse an ISO-8601 time string or a combined dateTime string to a
    ``time`` object.

    FHIR ``dateTime`` looks like ``2024-03-15T10:30:00+00:00``;
    FHIR ``time``      looks like ``10:30:00``.
    """
    if not value:
        return None
    if "T" in value:
        # dateTime — extract the time portion, strip timezone
        time_part = value.split("T", 1)[1]
        # remove timezone suffix (+HH:MM, -HH:MM, or Z)
        for sep in ("+", "-", "Z"):
            time_part = time_part.split(sep)[0]
        return datetime.strptime(time_part[:8], "%H:%M:%S").time()
    # plain time string
    return datetime.strptime(value[:8], "%H:%M:%S").time()


def _parse_timezone_offset(value: Optional[str]) -> Optional[str]:
    """
    Extract a DICOM-style timezone offset string (e.g. ``+0500``) from a
    FHIR dateTime string or return the value unchanged if it already looks
    like a DICOM offset.
    """
    if not value:
        return None
    if "T" in value:
        # try to pull the offset from a dateTime
        for sep in ("+", "-"):
            if sep in value[10:]:
                idx = value.index(sep, 10)
                offset = value[idx:].replace(":", "")
                return offset[:5]  # e.g. +0500
        if value.endswith("Z"):
            return "+0000"
    return value


def _fhir_name_to_dicom(name_resource: Optional[Dict[str, Any]]) -> Optional[DICOMPersonName]:
    """
    Convert a FHIR HumanName dict to a :class:`DICOMPersonName`.

    FHIR HumanName fields used:
        family  → family_name
        given   → given_names[0] as first name, given[1] as middle_name
        prefix  → prefix (first element)
        suffix  → suffix (first element)

    The DICOM PN component order is Family^Given^Middle^Prefix^Suffix;
    FHIR does not have a dedicated middle-name field so ``given[1]``
    is promoted to middle name when present.
    """
    if not name_resource:
        return None

    given: List[str] = name_resource.get("given", [])
    first_names = [given[0]] if given else None
    middle_name = given[1] if len(given) > 1 else None

    prefixes: List[str] = name_resource.get("prefix", [])
    suffixes: List[str] = name_resource.get("suffix", [])

    return DICOMPersonName(
        family_name=name_resource.get("family"),
        given_names=first_names,
        middle_name=middle_name,
        prefix=prefixes[0] if prefixes else None,
        suffix=suffixes[0] if suffixes else None,
    )


def _coding_code(coding_list: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """Return the ``code`` of the first element in a FHIR Coding list."""
    if coding_list:
        return coding_list[0].get("code")
    return None


def _modalities_from_series(series_list: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Collect unique modality codes across all series."""
    modalities: List[str] = []
    for series in series_list or []:
        modality_cc: Dict = series.get("modality") or {}
        # R5/R6: modality is a CodeableConcept
        code = _coding_code(modality_cc.get("coding")) or modality_cc.get("text")
        if code and code not in modalities:
            modalities.append(code)
    return modalities or ["OT"]  # OT = Other; safe fallback


# ---------------------------------------------------------------------------
# Primary conversion functions
# ---------------------------------------------------------------------------

def fhir_imaging_study_to_dicom_study(
    imaging_study: Dict[str, Any],
) -> DICOMQueryStudy:
    """
    Convert a FHIR R5/R6 ``ImagingStudy`` resource dict to a
    :class:`DICOMQueryStudy`.

    Parameters
    ----------
    imaging_study:
        A Python dict representing the FHIR ImagingStudy JSON resource.

    Returns
    -------
    DICOMQueryStudy
    """
    # --- Study Instance UID ---
    # The DICOM UID is stored as an Identifier with system "urn:dicom:uid"
    # and a value prefixed with "urn:oid:".
    study_instance_uid = ""
    accession_number = ""
    for ident in imaging_study.get("identifier", []):
        if ident.get("system") == "urn:dicom:uid":
            study_instance_uid = ident.get("value", "").removeprefix("urn:oid:")
        else:
            # First non-DICOM-UID identifier is treated as the accession number
            if not accession_number:
                accession_number = ident.get("value", "")

    # --- Study Date / Time ---
    started: Optional[str] = imaging_study.get("started")
    study_date_obj: date = _parse_date(started) or date.today()
    study_time_obj: time = _parse_time(started) or time(0, 0, 0)
    tz_offset: Optional[str] = _parse_timezone_offset(started)

    # --- Patient demographics ---
    # The subject is typically a Patient reference ("Patient/123").
    # If a contained Patient resource is present, extract demographics from it.
    subject: Dict[str, Any] = imaging_study.get("subject", {})
    patient_name = DICOMPersonName(family_name="Unknown")
    patient_id: str = subject.get("reference", "").split("/")[-1] or "UNKNOWN"
    patient_birth_date: Optional[date] = None
    patient_sex: str = "O"  # DICOM values: M / F / O

    gender_map = {"male": "M", "female": "F", "other": "O", "unknown": "O"}

    for contained in imaging_study.get("contained", []):
        if contained.get("resourceType") == "Patient":
            names: List[Dict] = contained.get("name", [])
            official = next(
                (n for n in names if n.get("use") == "official"),
                names[0] if names else None,
            )
            patient_name = _fhir_name_to_dicom(official) or patient_name
            patient_id = contained.get("id", patient_id)
            patient_birth_date = _parse_date(contained.get("birthDate"))
            patient_sex = gender_map.get(contained.get("gender", "unknown"), "O")
            break

    # --- Referring Physician ---
    # R5 field is "referrer" (single Reference); some profiles use a list
    referrer_field = imaging_study.get("referrer")
    referring_physician: Optional[DICOMPersonName] = None
    if referrer_field:
        display: Optional[str] = referrer_field.get("display")
        if display:
            referring_physician = DICOMPersonName(family_name=display)

    # --- Modalities in Study ---
    series_list: List[Dict] = imaging_study.get("series", [])
    modalities = _modalities_from_series(series_list)

    # --- Counts ---
    number_of_series: int = imaging_study.get("numberOfSeries") or len(series_list)
    number_of_instances: int = imaging_study.get("numberOfInstances") or sum(
        s.get("numberOfInstances", len(s.get("instance", []))) for s in series_list
    )

    # --- Study Description / Study ID ---
    study_description: str = imaging_study.get("description", "")
    study_id: str = imaging_study.get("id", "")

    return DICOMQueryStudy(
        study_instance_uid=study_instance_uid,
        specific_character_set="ISO_IR 192",  # UTF-8; universally safe default
        study_date=study_date_obj,
        study_time=study_time_obj,
        accession_number=accession_number,
        modalities_in_study=modalities,
        referring_physician_name=referring_physician,
        timezone_offset_from_utc=tz_offset,
        patient_name=patient_name,
        patient_id=patient_id,
        patient_birth_date=patient_birth_date,
        patient_sex=patient_sex,
        study_id=study_id,
        study_description=study_description,
        number_of_study_related_series=number_of_series,
        number_of_study_related_instances=number_of_instances,
    )


def fhir_series_to_dicom_series(
    fhir_series: Dict[str, Any],
    dicom_study: DICOMQueryStudy,
) -> DICOMQuerySeries:
    """
    Convert a single FHIR ``ImagingStudy.series`` element to a
    :class:`DICOMQuerySeries`.

    Parameters
    ----------
    fhir_series:
        A Python dict for one element of ``ImagingStudy.series``.
    dicom_study:
        The already-converted :class:`DICOMQueryStudy` parent.

    Returns
    -------
    DICOMQuerySeries
    """
    series_instance_uid: str = fhir_series.get("uid", "")

    # Modality: CodeableConcept in R5/R6
    modality_cc: Dict = fhir_series.get("modality") or {}
    modality: str = (
        _coding_code(modality_cc.get("coding")) or modality_cc.get("text") or "OT"
    )

    series_description: Optional[str] = fhir_series.get("description")
    series_number: str = str(fhir_series.get("number", ""))

    # Performed Procedure Step start date/time from series.started
    started: Optional[str] = fhir_series.get("started")
    pps_date: Optional[date] = _parse_date(started)
    pps_time: Optional[time] = _parse_time(started)

    # Scheduled / Requested Procedure Step IDs are not core FHIR fields;
    # look for them in extensions using well-known URL fragments.
    scheduled_step_id: Optional[str] = None
    requested_proc_id: Optional[str] = None
    for ext in fhir_series.get("extension", []):
        url: str = ext.get("url", "")
        if "scheduledProcedureStepId" in url:
            scheduled_step_id = ext.get("valueString") or ext.get("valueId")
        elif "requestedProcedureId" in url:
            requested_proc_id = ext.get("valueString") or ext.get("valueId")

    number_of_instances: int = fhir_series.get("numberOfInstances") or len(
        fhir_series.get("instance", [])
    )

    return DICOMQuerySeries(
        series_instance_uid=series_instance_uid,
        modality=modality,
        series_description=series_description,
        series_number=series_number,
        performed_procedure_step_start_date=pps_date,
        performed_procedure_step_start_time=pps_time,
        scheduled_procedure_step_id=scheduled_step_id,
        requested_procedure_id=requested_proc_id,
        number_of_series_related_instances=number_of_instances,
        study=dicom_study,
    )


def fhir_instance_to_dicom_instance(
    fhir_instance: Dict[str, Any],
    dicom_study: DICOMQueryStudy,
    dicom_series: DICOMQuerySeries,
) -> DICOMQueryInstance:
    """
    Convert a single FHIR ``ImagingStudy.series.instance`` element to a
    :class:`DICOMQueryInstance`.

    Parameters
    ----------
    fhir_instance:
        A Python dict for one element of ``ImagingStudy.series.instance``.
    dicom_study:
        The already-converted :class:`DICOMQueryStudy` parent.
    dicom_series:
        The already-converted :class:`DICOMQuerySeries` parent.

    Returns
    -------
    DICOMQueryInstance
    """
    sop_instance_uid: str = fhir_instance.get("uid", "")

    # SOP Class UID — R5: sopClass is a Coding (not CodeableConcept)
    sop_class: Dict = fhir_instance.get("sopClass") or {}
    sop_class_uid: str = sop_class.get("code") or sop_class.get("value", "")

    instance_number: int = fhir_instance.get("number", 0)

    # Pixel-level attributes are not part of core FHIR ImagingStudy;
    # they may appear as extensions using well-known URL fragments.
    rows: Optional[int] = None
    columns: Optional[int] = None
    bits_allocated: Optional[int] = None
    number_of_frames: Optional[int] = None

    for ext in fhir_instance.get("extension", []):
        url: str = ext.get("url", "").lower()
        val: Optional[int] = ext.get("valueInteger") or ext.get("valueUnsignedInt")
        if "rows" in url:
            rows = val
        elif "columns" in url:
            columns = val
        elif "bitsallocated" in url or "bits-allocated" in url:
            bits_allocated = val
        elif "numberofframes" in url or "number-of-frames" in url:
            number_of_frames = val

    return DICOMQueryInstance(
        sop_instance_uid=sop_instance_uid,
        sop_class_uid=sop_class_uid,
        # Inherit timezone offset from study
        timezone_offset_from_utc=dicom_study.timezone_offset_from_utc,
        instance_number=instance_number,
        rows=rows,
        columns=columns,
        bits_allocated=bits_allocated,
        number_of_frames=number_of_frames,
        study=dicom_study,
        series=dicom_series,
    )


# ---------------------------------------------------------------------------
# Convenience: convert an entire ImagingStudy resource at once
# ---------------------------------------------------------------------------

def fhir_imaging_study_to_dicom_models(
    imaging_study: Dict[str, Any],
) -> Tuple[DICOMQueryStudy, List[DICOMQuerySeries], List[DICOMQueryInstance]]:
    """
    Convert a complete FHIR R5/R6 ``ImagingStudy`` resource to the full set
    of DICOM query model objects in a single call.

    Parameters
    ----------
    imaging_study:
        A Python dict representing the FHIR ImagingStudy JSON resource.

    Returns
    -------
    (DICOMQueryStudy, list[DICOMQuerySeries], list[DICOMQueryInstance])
        All series and instances are included in flat lists; the study/series
        hierarchy is preserved via back-references on each object.

    Example
    -------
    >>> import json
    >>> with open("imaging_study.json") as f:
    ...     resource = json.load(f)
    >>> study, series_list, instance_list = fhir_imaging_study_to_dicom_models(resource)
    >>> dicom_json = study.to_dicom_json("https://dicom.example.com/wado/rs")
    """
    dicom_study = fhir_imaging_study_to_dicom_study(imaging_study)

    all_series: List[DICOMQuerySeries] = []
    all_instances: List[DICOMQueryInstance] = []

    for fhir_series in imaging_study.get("series", []):
        dicom_series = fhir_series_to_dicom_series(fhir_series, dicom_study)
        all_series.append(dicom_series)

        for fhir_inst in fhir_series.get("instance", []):
            dicom_inst = fhir_instance_to_dicom_instance(fhir_inst, dicom_study, dicom_series)
            all_instances.append(dicom_inst)

    return dicom_study, all_series, all_instances