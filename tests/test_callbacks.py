"""Tests for DICOM QIDO metadata callback helper functions.

Only the pure, database-free functions are tested here (ton, create_person_name,
create_study, create_series, create_instance). The async update_meta_data_qido_async
function requires a live database and is not covered here.
"""

import pytest
from app.callbacks.dcm_qido_meta_data import (
    ton,
    create_person_name,
    create_study,
    create_series,
    create_instance,
)
from app.services.query_services.sql_query_service.model import (
    DICOMQueryStudy as SQLDCMStudy,
    DICOMQuerySeries as SQLDCMSeries,
    DICOMQueryInstance as SQLDCMInstance,
)


# ---------------------------------------------------------------------------
# ton() – tag-or-none extractor
# ---------------------------------------------------------------------------

class TestTon:
    def test_existing_tag_returns_first_value(self):
        meta = {"00100020": {"vr": "LO", "Value": ["P001"]}}
        assert ton(meta, "00100020") == "P001"

    def test_missing_tag_returns_none(self):
        meta = {}
        assert ton(meta, "00100020") is None

    def test_tag_without_value_returns_none(self):
        meta = {"00100020": {"vr": "LO"}}
        assert ton(meta, "00100020") is None

    def test_numeric_value(self):
        meta = {"00280010": {"vr": "US", "Value": [512]}}
        assert ton(meta, "00280010") == 512

    def test_nested_dict_value(self):
        meta = {"00100010": {"vr": "PN", "Value": [{"Alphabetic": "Smith^John^^^"}]}}
        result = ton(meta, "00100010")
        assert isinstance(result, dict)
        assert "Alphabetic" in result

    def test_empty_value_list_raises_index_error(self):
        # ton() only catches KeyError; an empty Value list raises IndexError
        meta = {"00100020": {"vr": "LO", "Value": []}}
        with pytest.raises(IndexError):
            ton(meta, "00100020")


# ---------------------------------------------------------------------------
# create_person_name()
# ---------------------------------------------------------------------------

class TestCreatePersonName:
    def test_string_with_all_components(self):
        result = create_person_name("Smith^John^M^Dr^Jr", "pn_")
        assert result["pn_family_name"] == "Smith"
        assert result["pn_given_name"] == "John"
        assert result["pn_middle_name"] == "M"
        assert result["pn_prefix"] == "Dr"
        assert result["pn_suffix"] == "Jr"

    def test_string_partial_components(self):
        result = create_person_name("Smith^John", "pn_")
        assert result["pn_family_name"] == "Smith"
        assert result["pn_given_name"] == "John"
        assert result["pn_middle_name"] == ""
        assert result["pn_prefix"] == ""
        assert result["pn_suffix"] == ""

    def test_empty_string_all_empty(self):
        result = create_person_name("", "pn_")
        for key in ["pn_family_name", "pn_given_name", "pn_middle_name", "pn_prefix", "pn_suffix"]:
            assert result[key] == ""

    def test_dict_input_alphabetic(self):
        result = create_person_name({"Alphabetic": "Jones^Alice^^^"}, "pn_")
        assert result["pn_family_name"] == "Jones"
        assert result["pn_given_name"] == "Alice"

    def test_custom_prefix(self):
        result = create_person_name("Smith^John^^^", "rpn_")
        assert "rpn_family_name" in result
        assert "rpn_given_name" in result

    def test_returns_five_keys(self):
        result = create_person_name("Smith^John^M^Dr^Jr", "pn_")
        assert len(result) == 5

    def test_string_without_caret(self):
        # No caret → treated as all-empty (spec: only split if ^ present)
        result = create_person_name("SmithJohn", "pn_")
        # All components should be empty since no ^ found
        for key in ["pn_family_name", "pn_given_name", "pn_middle_name", "pn_prefix", "pn_suffix"]:
            assert result[key] == ""


# ---------------------------------------------------------------------------
# create_study()
# ---------------------------------------------------------------------------

class TestCreateStudy:
    def test_returns_sql_study(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert isinstance(study, SQLDCMStudy)

    def test_study_uid_populated(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.study_instance_uid == "1.2.3.4.5.6.7"

    def test_study_date_parsed(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.study_date.year == 2024
        assert study.study_date.month == 1
        assert study.study_date.day == 15

    def test_study_time_parsed(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.study_time.hour == 14
        assert study.study_time.minute == 30
        assert study.study_time.second == 0

    def test_patient_id(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.patient_id == "PID001"

    def test_patient_name_components(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.pn_family_name == "Smith"
        assert study.pn_given_name == "John"

    def test_accession_number(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.accession_number == "ACC001"

    def test_study_description(self, sample_meta_json):
        study = create_study(sample_meta_json)
        assert study.study_description == "Chest CT"

    def test_default_character_set_when_absent(self, sample_meta_json):
        # 00080005 not in sample_meta_json → defaults to ISO-IR 6
        assert "00080005" not in sample_meta_json
        study = create_study(sample_meta_json)
        assert study.specific_character_set == "ISO-IR 6"

    def test_study_time_with_fractional_seconds(self, sample_meta_json):
        # Fractional seconds should be stripped before parsing
        meta = dict(sample_meta_json)
        meta["00080030"] = {"vr": "TM", "Value": ["143000.123456"]}
        study = create_study(meta)
        assert study.study_time.second == 0


# ---------------------------------------------------------------------------
# create_series()
# ---------------------------------------------------------------------------

class TestCreateSeries:
    def test_returns_sql_series(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert isinstance(series, SQLDCMSeries)

    def test_series_uid(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert series.series_instance_uid == "1.2.3.4.5.6.7.8"

    def test_modality(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert series.modality == "CT"

    def test_series_description(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert series.series_description == "Axial slices"

    def test_series_number(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert series.series_number == "1"

    def test_study_relationship(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        assert series.study is study

    def test_performed_procedure_step_date(self, sample_meta_json):
        meta = dict(sample_meta_json)
        meta["00400244"] = {"vr": "DA", "Value": ["20240115"]}
        study = create_study(meta)
        series = create_series(meta, study)
        assert series.performed_procedure_step_start_date.year == 2024

    def test_performed_procedure_step_time(self, sample_meta_json):
        meta = dict(sample_meta_json)
        meta["00400245"] = {"vr": "TM", "Value": ["090000"]}
        study = create_study(meta)
        series = create_series(meta, study)
        assert series.performed_procedure_step_start_time.hour == 9

    def test_performed_procedure_step_time_with_fraction(self, sample_meta_json):
        meta = dict(sample_meta_json)
        meta["00400245"] = {"vr": "TM", "Value": ["090000.500"]}
        study = create_study(meta)
        series = create_series(meta, study)
        assert series.performed_procedure_step_start_time.hour == 9


# ---------------------------------------------------------------------------
# create_instance()
# ---------------------------------------------------------------------------

class TestCreateInstance:
    def _setup(self, sample_meta_json):
        study = create_study(sample_meta_json)
        series = create_series(sample_meta_json, study)
        return study, series

    def test_returns_sql_instance(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert isinstance(instance, SQLDCMInstance)

    def test_sop_instance_uid(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.sop_instance_uid == "1.2.3.4.5.6.7.8.9"

    def test_sop_class_uid(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.sop_class_uid == "1.2.840.10008.5.1.4.1.1.2"

    def test_rows_and_columns(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.rows == 512
        assert instance.columns == 512

    def test_bits_allocated(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.bits_allocated == 16

    def test_number_of_frames(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.number_of_frames == 1

    def test_study_and_series_relationships(self, sample_meta_json):
        study, series = self._setup(sample_meta_json)
        instance = create_instance(sample_meta_json, study, series)
        assert instance.study is study
        assert instance.series is series
