"""Shared fixtures and configuration for the forte-pacs test suite.

Environment variables for dynaconf must be set before any app.* imports
occur, so they are set at module level here.
"""

import os
import tempfile
import json
import pytest

# Provide minimal settings so dynaconf validators pass when app modules are imported
os.environ.setdefault("DYNACONF_DATA_SERVICE", "fs_data_service")
os.environ.setdefault("DYNACONF_TASK_QUEUE_SERVICE", "rq_task_service")
os.environ.setdefault("DYNACONF_QUERY_SERVICE", "none")
os.environ.setdefault("DYNACONF_SERVER_BASE_URL", "http://localhost:8000/")


# ---------------------------------------------------------------------------
# Shared DICOM metadata fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_meta_json():
    """Minimal valid DICOM metadata JSON that satisfies create_study/series/instance."""
    return {
        # SOP class / instance
        "00080016": {"vr": "UI", "Value": ["1.2.840.10008.5.1.4.1.1.2"]},  # SOPClassUID
        "00080018": {"vr": "UI", "Value": ["1.2.3.4.5.6.7.8.9"]},          # SOPInstanceUID
        # Study level
        "00080020": {"vr": "DA", "Value": ["20240115"]},                    # StudyDate
        "00080030": {"vr": "TM", "Value": ["143000"]},                      # StudyTime
        "00080050": {"vr": "SH", "Value": ["ACC001"]},                      # AccessionNumber
        "00081030": {"vr": "LO", "Value": ["Chest CT"]},                    # StudyDescription
        # Patient
        "00100010": {"vr": "PN", "Value": [{"Alphabetic": "Smith^John^M^^"}]},
        "00100020": {"vr": "LO", "Value": ["PID001"]},                      # PatientID
        "00100040": {"vr": "CS", "Value": ["M"]},                           # PatientSex
        # UIDs
        "0020000D": {"vr": "UI", "Value": ["1.2.3.4.5.6.7"]},              # StudyInstanceUID
        "0020000E": {"vr": "UI", "Value": ["1.2.3.4.5.6.7.8"]},            # SeriesInstanceUID
        "00200010": {"vr": "SH", "Value": ["STU001"]},                      # StudyID
        # Series level
        "00080060": {"vr": "CS", "Value": ["CT"]},                          # Modality
        "0008103E": {"vr": "LO", "Value": ["Axial slices"]},                # SeriesDescription
        "00200011": {"vr": "IS", "Value": [1]},                             # SeriesNumber
        # Instance level
        "00200013": {"vr": "IS", "Value": [1]},                             # InstanceNumber
        "00280008": {"vr": "IS", "Value": [1]},                             # NumberOfFrames
        "00280010": {"vr": "US", "Value": [512]},                           # Rows
        "00280011": {"vr": "US", "Value": [512]},                           # Columns
        "00280100": {"vr": "US", "Value": [16]},                            # BitsAllocated
    }


@pytest.fixture
def study_uid():
    return "1.2.3.4.5.6.7"


@pytest.fixture
def series_uid():
    return "1.2.3.4.5.6.7.8"


@pytest.fixture
def instance_uid():
    return "1.2.3.4.5.6.7.8.9"


@pytest.fixture
def temp_storage_dir():
    """Temporary directory for FSDataService tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
