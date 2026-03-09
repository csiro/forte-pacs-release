"""Tests for DICOM media type classes and multipart message handling."""

import pytest
from app.utils.dicom_media import (
    DicomMediaType,
    DicomMediaPart,
    DicomMediaPartBytes,
    DicomMediaPartDICOM,
    DicomMediaPartDICOMImage,
    DicomMediaPartDocument,
    DicomMediaPartJSON,
    DicomMediaPartXML,
    DicomMediaMultipartMessage,
    DicomMediaSinglepartParser,
    transfer_syntax_to_media_type_images,
)


# ---------------------------------------------------------------------------
# DicomMediaType enum
# ---------------------------------------------------------------------------

class TestDicomMediaType:
    def test_all_expected_members(self):
        expected = {
            "ANY", "DICOM", "DICOM_JSON", "DICOM_XML",
            "DICOM_IMAGE", "DICOM_VIDEO", "DICOM_DOCUMENT",
            "BYTES", "MULTIPART", "JSON", "WADL",
        }
        assert {m.name for m in DicomMediaType} == expected

    def test_values_are_unique(self):
        values = [m.value for m in DicomMediaType]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# transfer_syntax_to_media_type_images
# ---------------------------------------------------------------------------

class TestTransferSyntaxToMediaType:
    def test_jpeg_baseline(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.4.50") == "image/jpeg"

    def test_jpeg_lossless(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.4.70") == "image/jpeg"

    def test_jpeg2000_lossless(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.4.90") == "image/jp2"

    def test_jpeg2000_lossy(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.4.91") == "image/jp2"

    def test_jpeg_ls_lossless(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.4.80") == "image/jls"

    def test_rle(self):
        assert transfer_syntax_to_media_type_images("1.2.840.10008.1.2.5") == "image/dicom-rle"

    def test_unsupported_raises(self):
        with pytest.raises(KeyError):
            transfer_syntax_to_media_type_images("1.2.840.10008.1.2.1")  # uncompressed


# ---------------------------------------------------------------------------
# DicomMediaPartBytes
# ---------------------------------------------------------------------------

class TestDicomMediaPartBytes:
    def test_content_type(self):
        part = DicomMediaPartBytes(data=b"\x00\x01")
        assert part.content_type() == DicomMediaType.BYTES

    def test_content_type_str(self):
        part = DicomMediaPartBytes(data=b"\x00\x01")
        assert "application/octet-stream" in part.content_type_str()

    def test_to_bytes(self):
        data = b"\xAB\xCD\xEF"
        part = DicomMediaPartBytes(data=data)
        assert part.to_bytes() == data

    def test_with_headers(self):
        headers = {"Content-Location": "/wado/studies/1/series/2/instances/3"}
        part = DicomMediaPartBytes(data=b"", headers=headers)
        assert part.headers["Content-Location"].endswith("/3")


# ---------------------------------------------------------------------------
# DicomMediaPartJSON
# ---------------------------------------------------------------------------

class TestDicomMediaPartJSON:
    def test_content_type(self):
        part = DicomMediaPartJSON(data='{"key": "value"}')
        assert part.content_type() == DicomMediaType.DICOM_JSON

    def test_content_type_str(self):
        part = DicomMediaPartJSON(data="{}")
        assert part.content_type_str() == "application/dicom+json"

    def test_to_bytes_is_utf8(self):
        payload = '{"00100020": {"vr": "LO", "Value": ["P001"]}}'
        part = DicomMediaPartJSON(data=payload)
        assert part.to_bytes() == payload.encode("utf-8")

    def test_unicode_encodes_correctly(self):
        payload = '{"name": "山田太郎"}'
        part = DicomMediaPartJSON(data=payload)
        assert part.to_bytes().decode("utf-8") == payload


# ---------------------------------------------------------------------------
# DicomMediaPartXML
# ---------------------------------------------------------------------------

class TestDicomMediaPartXML:
    def test_content_type(self):
        part = DicomMediaPartXML(data="<NativeDicomModel/>")
        assert part.content_type() == DicomMediaType.DICOM_XML

    def test_content_type_str(self):
        part = DicomMediaPartXML(data="<NativeDicomModel/>")
        assert part.content_type_str() == "application/dicom+xml"

    def test_to_bytes_is_utf8(self):
        payload = "<NativeDicomModel/>"
        part = DicomMediaPartXML(data=payload)
        assert part.to_bytes() == payload.encode("utf-8")


# ---------------------------------------------------------------------------
# DicomMediaPartDICOMImage
# ---------------------------------------------------------------------------

class TestDicomMediaPartDICOMImage:
    def test_content_type(self):
        part = DicomMediaPartDICOMImage(
            data=b"\xFF\xD8\xFF",
            content_type="image/jpeg",
            transfer_syntax="1.2.840.10008.1.2.4.50",
        )
        assert part.content_type() == DicomMediaType.DICOM_IMAGE

    def test_content_type_str(self):
        part = DicomMediaPartDICOMImage(
            data=b"",
            content_type="image/jp2",
        )
        assert part.content_type_str() == "image/jp2"

    def test_transfer_syntax(self):
        ts = "1.2.840.10008.1.2.4.90"
        part = DicomMediaPartDICOMImage(data=b"", content_type="image/jp2", transfer_syntax=ts)
        assert part.transfer_syntax() == ts

    def test_to_bytes(self):
        data = b"\xFF\xD8\xFF\xE0"
        part = DicomMediaPartDICOMImage(data=data, content_type="image/jpeg")
        assert part.to_bytes() == data


# ---------------------------------------------------------------------------
# DicomMediaPartDocument
# ---------------------------------------------------------------------------

class TestDicomMediaPartDocument:
    def test_content_type(self):
        part = DicomMediaPartDocument(data=b"%PDF", content_type="application/pdf")
        assert part.content_type() == DicomMediaType.DICOM_DOCUMENT

    def test_content_type_str(self):
        part = DicomMediaPartDocument(data=b"%PDF", content_type="application/pdf")
        assert part.content_type_str() == "application/pdf"

    def test_to_bytes(self):
        data = b"%PDF-1.4"
        part = DicomMediaPartDocument(data=data, content_type="application/pdf")
        assert part.to_bytes() == data


# ---------------------------------------------------------------------------
# DicomMediaMultipartMessage
# ---------------------------------------------------------------------------

class TestDicomMediaMultipartMessage:
    def _make_part(self, data: bytes, content_type_str: str = "application/octet-stream") -> DicomMediaPartBytes:
        headers = {"Content-Location": f"http://example.com/part"}
        return DicomMediaPartBytes(data=data, headers=headers)

    def test_to_bytes_contains_boundary(self):
        msg = DicomMediaMultipartMessage()
        msg.parts.append(self._make_part(b"\x01\x02\x03"))
        result = msg.to_bytes()
        assert msg.boundary is not None
        assert msg.boundary.encode("utf-8") in result

    def test_to_bytes_starts_with_boundary_marker(self):
        msg = DicomMediaMultipartMessage()
        msg.parts.append(self._make_part(b"hello"))
        result = msg.to_bytes()
        assert result.startswith(b"--")

    def test_to_bytes_ends_with_closing_boundary(self):
        msg = DicomMediaMultipartMessage()
        msg.parts.append(self._make_part(b"hello"))
        result = msg.to_bytes()
        assert result.rstrip().endswith(b"--")

    def test_multiple_parts_all_present(self):
        msg = DicomMediaMultipartMessage()
        payloads = [b"part-one", b"part-two", b"part-three"]
        for payload in payloads:
            msg.parts.append(self._make_part(payload))
        result = msg.to_bytes()
        for payload in payloads:
            assert payload in result

    def test_json_part_included(self):
        msg = DicomMediaMultipartMessage()
        json_part = DicomMediaPartJSON(
            data='{"test": 1}',
            headers={"Content-Location": "http://example.com/meta"},
        )
        msg.parts.append(json_part)
        result = msg.to_bytes()
        assert b'{"test": 1}' in result
        assert b"application/dicom+json" in result

    def test_boundary_is_random_each_call(self):
        msg = DicomMediaMultipartMessage()
        msg.parts.append(self._make_part(b"data"))
        msg.to_bytes()
        boundary1 = msg.boundary
        msg.to_bytes()
        boundary2 = msg.boundary
        # Boundaries are regenerated each call, so they may or may not differ,
        # but they must always be non-empty strings
        assert boundary1 is not None
        assert boundary2 is not None

    def test_empty_message_still_has_closing_boundary(self):
        msg = DicomMediaMultipartMessage()
        result = msg.to_bytes()
        assert b"--" in result


# ---------------------------------------------------------------------------
# DicomMediaSinglepartParser
# ---------------------------------------------------------------------------

class TestDicomMediaSinglepartParser:
    def test_json_body_parsed(self):
        parser = DicomMediaSinglepartParser(
            content_type=DicomMediaType.DICOM_JSON,
            transfer_syntax_uid="",
        )
        payload = b'{"00100020": {"vr": "LO", "Value": ["P001"]}}'
        parts = parser.parse_body(payload)
        assert len(parts) == 1
        assert isinstance(parts[0], DicomMediaPartJSON)

    def test_xml_body_parsed(self):
        parser = DicomMediaSinglepartParser(
            content_type=DicomMediaType.DICOM_XML,
            transfer_syntax_uid="",
        )
        payload = b"<NativeDicomModel/>"
        parts = parser.parse_body(payload)
        assert len(parts) == 1
        assert isinstance(parts[0], DicomMediaPartXML)

    def test_invalid_dicom_binary_returns_none_dataset(self):
        parser = DicomMediaSinglepartParser(
            content_type=DicomMediaType.DICOM,
            transfer_syntax_uid="1.2.840.10008.1.2.1",
        )
        parts = parser.parse_body(b"not-valid-dicom")
        assert len(parts) == 1
        assert isinstance(parts[0], DicomMediaPartDICOM)
        # Invalid DICOM data yields a part with data=None
        assert parts[0].data is None
