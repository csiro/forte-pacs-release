"""Tests for HTTP Accept header parsing utilities."""

import pytest
from app.utils.accept_headers import (
    parse_media_range,
    parse_accept_charset_query,
    AcceptHeaders,
    AcceptType,
    AcceptHeaderField,
)
from app.utils.dicom_media import DicomMediaType


# ---------------------------------------------------------------------------
# parse_media_range
# ---------------------------------------------------------------------------

class TestParseMediaRange:
    def test_dicom_xml(self):
        assert parse_media_range("application/dicom+xml") == DicomMediaType.DICOM_XML

    def test_dicom_json(self):
        assert parse_media_range("application/dicom+json") == DicomMediaType.DICOM_JSON

    def test_dicom_binary(self):
        assert parse_media_range("application/dicom") == DicomMediaType.DICOM

    def test_octet_stream(self):
        assert parse_media_range("application/octet-stream") == DicomMediaType.BYTES

    def test_image_type(self):
        assert parse_media_range("image/jpeg") == DicomMediaType.DICOM_IMAGE

    def test_image_jp2(self):
        assert parse_media_range("image/jp2") == DicomMediaType.DICOM_IMAGE

    def test_video_type(self):
        assert parse_media_range("video/mpeg") == DicomMediaType.DICOM_VIDEO

    def test_wadl(self):
        assert parse_media_range("application/vnd.sun.wadl+xml") == DicomMediaType.WADL

    def test_application_json(self):
        assert parse_media_range("application/json") == DicomMediaType.JSON

    def test_wildcard(self):
        assert parse_media_range("*/*") == DicomMediaType.ANY

    def test_unknown_returns_any(self):
        assert parse_media_range("text/plain") == DicomMediaType.ANY

    def test_multipart_related_with_dicom_json(self):
        # The media_range passed in is the outer type in multipart; when it contains
        # application/dicom+json it maps to DICOM_JSON
        assert parse_media_range("multipart/related; type=application/dicom+json") == DicomMediaType.DICOM_JSON


# ---------------------------------------------------------------------------
# parse_accept_charset_query
# ---------------------------------------------------------------------------

class TestParseAcceptCharsetQuery:
    def test_none_accept_returns_empty_types(self):
        result = parse_accept_charset_query(accept=None, charset=None)
        assert isinstance(result, AcceptHeaders)
        assert result.accept_types == []
        assert result.charsets == []

    def test_single_dicom_json_accept(self):
        result = parse_accept_charset_query(accept="application/dicom+json")
        assert len(result.accept_types) == 1
        assert result.accept_types[0].type == DicomMediaType.DICOM_JSON

    def test_multiple_accept_types(self):
        accept_str = "application/dicom+json, application/dicom+xml"
        result = parse_accept_charset_query(accept=accept_str)
        assert len(result.accept_types) == 2
        types = {at.type for at in result.accept_types}
        assert DicomMediaType.DICOM_JSON in types
        assert DicomMediaType.DICOM_XML in types

    def test_quality_factor_parsed(self):
        accept_str = "application/dicom+json;q=0.9, application/dicom+xml;q=0.8"
        result = parse_accept_charset_query(accept=accept_str)
        qualities = {at.quality for at in result.accept_types}
        assert 0.9 in qualities
        assert 0.8 in qualities

    def test_non_multipart_not_marked_multipart(self):
        result = parse_accept_charset_query(accept="application/dicom+json")
        assert result.accept_types[0].is_multipart is False

    def test_transfer_syntax_in_media_type_params(self):
        # webob's Accept parser accepts single-type headers with transfer-syntax param
        accept_str = "application/octet-stream; transfer-syntax=1.2.840.10008.1.2.4.50"
        result = parse_accept_charset_query(accept=accept_str)
        assert result.accept_types[0].transfer_syntax == "1.2.840.10008.1.2.4.50"

    def test_multipart_rejects_slashed_param_value(self):
        # webob's strict RFC parser rejects unquoted parameter values containing '/'
        accept_str = "multipart/related; type=application/dicom"
        with pytest.raises(ValueError):
            parse_accept_charset_query(accept=accept_str)

    def test_wildcard_accept(self):
        result = parse_accept_charset_query(accept="*/*")
        assert result.accept_types[0].type == DicomMediaType.ANY

    def test_empty_string_accept(self):
        # An empty string falsy — treated same as None
        result = parse_accept_charset_query(accept="", charset=None)
        assert result.accept_types == []


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------

class TestAcceptHeaderField:
    def test_default_quality(self):
        field = AcceptHeaderField(value="utf-8")
        assert field.quality == 1.0

    def test_custom_quality(self):
        field = AcceptHeaderField(value="iso-8859-1", quality=0.5)
        assert field.quality == 0.5


class TestAcceptType:
    def test_defaults(self):
        at = AcceptType(type=DicomMediaType.DICOM_JSON, media_type_str="application/dicom+json")
        assert at.is_multipart is True
        assert at.transfer_syntax is None
        assert at.charset is None
        assert at.quality == 1.0
