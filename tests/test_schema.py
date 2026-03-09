"""Tests for Pydantic schema models: DCMPixelData and DCMInstance."""

import json
import pytest
from app.schema.dicom_pixel_data import DCMPixelData
from app.schema.dicom_instance import DCMInstance


# ---------------------------------------------------------------------------
# DCMPixelData
# ---------------------------------------------------------------------------

class TestDCMPixelData:
    """Tests for the DCMPixelData Pydantic model."""

    def _minimal_pixel_data(self, **overrides) -> dict:
        base = {
            "number_of_frames": 1,
            "pixel_data_format": "native",
            "samples_per_pixel": 1,
            "photometric_interpretation": "MONOCHROME2",
            "rows": 512,
            "columns": 512,
            "bits_allocated": 16,
            "bits_stored": 12,
            "high_bit": 11,
            "pixel_representation": 0,
            "frames": [b"\x00\x01\x02\x03"],
        }
        base.update(overrides)
        return base

    def test_valid_construction(self):
        pd = DCMPixelData(**self._minimal_pixel_data())
        assert pd.rows == 512
        assert pd.columns == 512
        assert pd.number_of_frames == 1

    def test_optional_fields_default_none(self):
        pd = DCMPixelData(**self._minimal_pixel_data())
        assert pd.transfer_syntax_uid is None
        assert pd.planar_configuration is None
        assert pd.smallest_image_pixel_value is None
        assert pd.largest_image_pixel_value is None
        assert pd.red_palette_color_lookup_table_descriptor is None

    def test_optional_fields_can_be_set(self):
        pd = DCMPixelData(**self._minimal_pixel_data(
            transfer_syntax_uid="1.2.840.10008.1.2.1",
            planar_configuration=0,
            smallest_image_pixel_value=0,
            largest_image_pixel_value=4095,
        ))
        assert pd.transfer_syntax_uid == "1.2.840.10008.1.2.1"
        assert pd.planar_configuration == 0
        assert pd.largest_image_pixel_value == 4095

    def test_multiple_frames(self):
        frames = [b"\x00\x01", b"\x02\x03", b"\x04\x05"]
        pd = DCMPixelData(**self._minimal_pixel_data(number_of_frames=3, frames=frames))
        assert pd.number_of_frames == 3
        assert len(pd.frames) == 3

    def test_json_round_trip(self):
        """DCMPixelData must survive model_dump_json -> model_validate_json."""
        pd = DCMPixelData(**self._minimal_pixel_data(frames=[b"\xAB\xCD"]))
        json_str = pd.model_dump_json()
        restored = DCMPixelData.model_validate_json(json_str)
        assert restored.rows == pd.rows
        assert restored.columns == pd.columns
        assert restored.number_of_frames == pd.number_of_frames
        assert restored.photometric_interpretation == pd.photometric_interpretation
        assert restored.frames[0] == b"\xAB\xCD"

    def test_palette_color_descriptor(self):
        pd = DCMPixelData(**self._minimal_pixel_data(
            red_palette_color_lookup_table_descriptor=[256, 0, 8],
            green_palette_color_lookup_table_descriptor=[256, 0, 8],
            blue_palette_color_lookup_table_descriptor=[256, 0, 8],
        ))
        assert pd.red_palette_color_lookup_table_descriptor == [256, 0, 8]


# ---------------------------------------------------------------------------
# DCMInstance
# ---------------------------------------------------------------------------

class TestDCMInstance:
    """Tests for the DCMInstance Pydantic model."""

    def _minimal_instance(self, **overrides) -> dict:
        base = {
            "study_uid": "1.2.3.4.5.6.7",
            "series_uid": "1.2.3.4.5.6.7.8",
            "instance_uid": "1.2.3.4.5.6.7.8.9",
            "meta_data": "{}",
            "sop_class_uid": "1.2.840.10008.5.1.4.1.1.2",
        }
        base.update(overrides)
        return base

    def test_valid_minimal_construction(self):
        inst = DCMInstance(**self._minimal_instance())
        assert inst.study_uid == "1.2.3.4.5.6.7"
        assert inst.series_uid == "1.2.3.4.5.6.7.8"
        assert inst.instance_uid == "1.2.3.4.5.6.7.8.9"
        assert inst.sop_class_uid == "1.2.840.10008.5.1.4.1.1.2"

    def test_optional_fields_default_none(self):
        inst = DCMInstance(**self._minimal_instance())
        assert inst.pixel_data is None
        assert inst.other_bulk_data is None
        assert inst.encap_document_mediatype is None

    def test_with_pixel_data(self):
        pixel_data = DCMPixelData(
            number_of_frames=1,
            pixel_data_format="native",
            samples_per_pixel=1,
            photometric_interpretation="MONOCHROME2",
            rows=128,
            columns=128,
            bits_allocated=8,
            bits_stored=8,
            high_bit=7,
            pixel_representation=0,
            frames=[b"\xFF" * 128 * 128],
        )
        inst = DCMInstance(**self._minimal_instance(pixel_data=pixel_data))
        assert inst.pixel_data is not None
        assert inst.pixel_data.rows == 128

    def test_with_bulk_data(self):
        inst = DCMInstance(**self._minimal_instance(
            other_bulk_data={"00420011": b"pdf-content"},
        ))
        assert inst.other_bulk_data is not None
        assert b"pdf-content" in inst.other_bulk_data.values()

    def test_with_encapsulated_document_mediatype(self):
        inst = DCMInstance(**self._minimal_instance(
            encap_document_mediatype="application/pdf",
        ))
        assert inst.encap_document_mediatype == "application/pdf"

    def test_json_round_trip(self):
        """DCMInstance must survive model_dump_json -> model_validate_json."""
        inst = DCMInstance(**self._minimal_instance(
            meta_data=json.dumps({"00080060": {"vr": "CS", "Value": ["CT"]}}),
        ))
        json_str = inst.model_dump_json()
        restored = DCMInstance.model_validate_json(json_str)
        assert restored.study_uid == inst.study_uid
        assert restored.instance_uid == inst.instance_uid

    def test_json_round_trip_with_pixel_data(self):
        """DCMInstance with pixel data must survive JSON serialisation round trip."""
        pixel_data = DCMPixelData(
            number_of_frames=1,
            pixel_data_format="native",
            samples_per_pixel=1,
            photometric_interpretation="MONOCHROME2",
            rows=4,
            columns=4,
            bits_allocated=8,
            bits_stored=8,
            high_bit=7,
            pixel_representation=0,
            frames=[b"\x01\x02\x03\x04"],
        )
        inst = DCMInstance(**self._minimal_instance(pixel_data=pixel_data))
        restored = DCMInstance.model_validate_json(inst.model_dump_json())
        assert restored.pixel_data is not None
        assert restored.pixel_data.rows == 4
        assert restored.pixel_data.frames[0] == b"\x01\x02\x03\x04"
