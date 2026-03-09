"""Tests for DICOM query parsing logic in app.schema.query."""

import pytest
from fastapi import HTTPException
from app.schema.query import (
    MatchType,
    QueryLevel,
    QueryAttributeMatch,
    parse_query,
    study_level_attrs,
    series_level_attrs,
    instance_level_attrs,
    all_tags,
    attr_tags,
)


# ---------------------------------------------------------------------------
# Enum smoke tests
# ---------------------------------------------------------------------------

class TestMatchType:
    def test_all_members_present(self):
        expected = {
            "single_value", "list_of_uid", "universal", "wildcard",
            "range", "sequence", "empty", "multiple", "fuzzy",
        }
        assert {m.name for m in MatchType} == expected

    def test_values_are_unique(self):
        values = [m.value for m in MatchType]
        assert len(values) == len(set(values))


class TestQueryLevel:
    def test_three_levels(self):
        assert {l.name for l in QueryLevel} == {"study", "series", "instance"}

    def test_ordering(self):
        assert QueryLevel.study.value < QueryLevel.series.value < QueryLevel.instance.value


# ---------------------------------------------------------------------------
# QueryAttributeMatch
# ---------------------------------------------------------------------------

class TestQueryAttributeMatch:
    def test_construction(self):
        qam = QueryAttributeMatch(MatchType.single_value, QueryLevel.study, "PatientID", "P001")
        assert qam.match_type == MatchType.single_value
        assert qam.level == QueryLevel.study
        assert qam.attr_name == "PatientID"
        assert qam.value == "P001"

    def test_optional_value_defaults_to_none(self):
        qam = QueryAttributeMatch(MatchType.universal, QueryLevel.study, "PatientName")
        assert qam.value is None

    def test_list_value(self):
        qam = QueryAttributeMatch(MatchType.list_of_uid, QueryLevel.study, "StudyInstanceUID",
                                  ["1.2.3", "4.5.6"])
        assert isinstance(qam.value, list)
        assert len(qam.value) == 2


# ---------------------------------------------------------------------------
# Attribute dictionaries
# ---------------------------------------------------------------------------

class TestAttributeDicts:
    def test_study_attrs_have_correct_level(self):
        for name, (tag, vr, level) in study_level_attrs.items():
            assert level == QueryLevel.study, f"{name} should be study level"

    def test_series_attrs_have_correct_level(self):
        for name, (tag, vr, level) in series_level_attrs.items():
            assert level == QueryLevel.series, f"{name} should be series level"

    def test_instance_attrs_have_correct_level(self):
        for name, (tag, vr, level) in instance_level_attrs.items():
            assert level == QueryLevel.instance, f"{name} should be instance level"

    def test_all_tags_is_union(self):
        expected_keys = set(study_level_attrs) | set(series_level_attrs) | set(instance_level_attrs)
        assert set(all_tags.keys()) == expected_keys

    def test_attr_tags_reverse_mapping(self):
        # attr_tags maps hex tag -> attribute name
        for name, (tag, vr, level) in all_tags.items():
            assert attr_tags[tag] == name


# ---------------------------------------------------------------------------
# parse_query
# ---------------------------------------------------------------------------

class TestParseQuery:
    """Tests for parse_query using a plain dict (duck-typed MultiDict)."""

    # --- Single-value matching ---

    def test_single_value_patient_id(self):
        params = {"PatientID": "P001"}
        result = parse_query([QueryLevel.study], params)
        assert len(result) == 1
        assert result[0].match_type == MatchType.single_value
        assert result[0].attr_name == "PatientID"
        assert result[0].value == "P001"

    def test_single_value_by_tag_number(self):
        # PatientID is tag 00100020
        params = {"00100020": "P001"}
        result = parse_query([QueryLevel.study], params)
        assert len(result) == 1
        assert result[0].attr_name == "PatientID"

    # --- Wildcard matching ---

    def test_wildcard_asterisk_only_is_universal(self):
        params = {"PatientName": "*"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.universal

    def test_wildcard_with_partial_name(self):
        params = {"PatientName": "Sm*"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.wildcard

    def test_wildcard_question_mark(self):
        params = {"PatientName": "Sm?th"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.wildcard

    # --- Fuzzy matching ---

    def test_fuzzy_matching_for_person_name(self):
        params = {"fuzzymatching": "true", "PatientName": "Smith"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.fuzzy

    def test_no_fuzzy_matching_for_non_pn(self):
        params = {"fuzzymatching": "true", "PatientID": "P001"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.single_value

    # --- Date/range matching ---

    def test_date_range_matching(self):
        params = {"StudyDate": "20240101-20241231"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.range

    def test_date_single_value(self):
        params = {"StudyDate": "20240101"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.single_value

    # --- UID list matching ---

    def test_uid_list(self):
        params = {"StudyInstanceUID": "1.2.3\\4.5.6\\7.8.9"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.list_of_uid
        assert result[0].value == ["1.2.3", "4.5.6", "7.8.9"]

    def test_single_uid(self):
        params = {"StudyInstanceUID": "1.2.3.4.5"}
        result = parse_query([QueryLevel.study], params)
        assert result[0].match_type == MatchType.single_value

    # --- Empty value matching ---

    def test_empty_value_ignored_without_flag(self):
        params = {"PatientName": '""'}
        result = parse_query([QueryLevel.study], params)
        assert len(result) == 0

    def test_empty_value_with_flag(self):
        params = {"emptyvaluematching": True, "PatientName": '""'}
        result = parse_query([QueryLevel.study], params)
        assert len(result) == 1
        assert result[0].match_type == MatchType.empty

    # --- Multiple params ---

    def test_multiple_params_parsed(self):
        params = {"PatientID": "P001", "StudyDate": "20240101"}
        result = parse_query([QueryLevel.study], params)
        names = {r.attr_name for r in result}
        assert "PatientID" in names
        assert "StudyDate" in names

    # --- Control params are stripped ---

    def test_fuzzymatching_param_not_in_result(self):
        params = {"fuzzymatching": "true", "PatientID": "P001"}
        result = parse_query([QueryLevel.study], params)
        # Only PatientID should produce a result
        assert all(r.attr_name != "fuzzymatching" for r in result)

    # --- Multi-level queries ---

    def test_series_param_at_series_level(self):
        params = {"Modality": "CT"}
        result = parse_query([QueryLevel.series], params)
        assert len(result) == 1
        assert result[0].level == QueryLevel.series

    def test_instance_param_at_instance_level(self):
        params = {"SOPInstanceUID": "1.2.3.4"}
        result = parse_query([QueryLevel.instance], params)
        assert len(result) == 1
        assert result[0].level == QueryLevel.instance

    # --- Error cases ---

    def test_unsupported_param_raises_400(self):
        params = {"UnsupportedTag": "value"}
        with pytest.raises(HTTPException) as exc_info:
            parse_query([QueryLevel.study], params)
        assert exc_info.value.status_code == 400

    def test_study_param_at_wrong_level_raises_400(self):
        # PatientID is study-level; querying at instance level should fail
        params = {"PatientID": "P001"}
        with pytest.raises(HTTPException) as exc_info:
            parse_query([QueryLevel.instance], params)
        assert exc_info.value.status_code == 400

    def test_empty_params_returns_empty_list(self):
        result = parse_query([QueryLevel.study], {})
        assert result == []
