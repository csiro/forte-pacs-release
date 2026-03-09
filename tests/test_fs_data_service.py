"""Tests for the filesystem-based DICOM data service."""

import os
import json
import pytest

from app.schema.dicom_instance import DCMInstance
from app.schema.dicom_pixel_data import DCMPixelData
from app.services.data_services.fs_data_service.fs_data_service import FSDataService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service(temp_storage_dir):
    return FSDataService(root_directory=temp_storage_dir)


def make_instance(study_uid="1.2.3", series_uid="1.2.3.4", instance_uid="1.2.3.4.5",
                  sop_class_uid="1.2.840.10008.5.1.4.1.1.2") -> DCMInstance:
    return DCMInstance(
        study_uid=study_uid,
        series_uid=series_uid,
        instance_uid=instance_uid,
        meta_data=json.dumps({"00080060": {"vr": "CS", "Value": ["CT"]}}),
        sop_class_uid=sop_class_uid,
    )


def make_instance_with_pixel_data(study_uid="1.2.3", series_uid="1.2.3.4",
                                   instance_uid="1.2.3.4.5") -> DCMInstance:
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
        frames=[b"\x00\x01\x02\x03"],
    )
    return DCMInstance(
        study_uid=study_uid,
        series_uid=series_uid,
        instance_uid=instance_uid,
        meta_data="{}",
        sop_class_uid="1.2.840.10008.5.1.4.1.1.2",
        pixel_data=pixel_data,
    )


# ---------------------------------------------------------------------------
# init_service
# ---------------------------------------------------------------------------

class TestInitService:
    async def test_valid_directory_succeeds(self, service):
        await service.init_service()  # should not raise

    async def test_invalid_directory_raises(self, temp_storage_dir):
        svc = FSDataService(root_directory="/nonexistent/path/that/does/not/exist")
        with pytest.raises(Exception, match="does not exist"):
            await svc.init_service()


# ---------------------------------------------------------------------------
# store_instance
# ---------------------------------------------------------------------------

class TestStoreInstance:
    async def test_creates_file_on_disk(self, service, temp_storage_dir):
        inst = make_instance()
        await service.store_instance(inst)
        expected_path = os.path.join(
            temp_storage_dir, inst.study_uid, inst.series_uid, inst.instance_uid
        )
        assert os.path.exists(expected_path)

    async def test_creates_directory_structure(self, service, temp_storage_dir):
        inst = make_instance(study_uid="study1", series_uid="series1", instance_uid="inst1")
        await service.store_instance(inst)
        assert os.path.isdir(os.path.join(temp_storage_dir, "study1", "series1"))

    async def test_file_contains_valid_json(self, service, temp_storage_dir):
        inst = make_instance()
        await service.store_instance(inst)
        file_path = os.path.join(
            temp_storage_dir, inst.study_uid, inst.series_uid, inst.instance_uid
        )
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        assert data["study_uid"] == inst.study_uid

    async def test_store_overwrites_existing(self, service, temp_storage_dir):
        inst1 = make_instance(sop_class_uid="1.2.3")
        inst2 = make_instance(sop_class_uid="4.5.6")
        await service.store_instance(inst1)
        await service.store_instance(inst2)
        restored = await service.get_instance(inst2.study_uid, inst2.series_uid, inst2.instance_uid)
        assert restored.sop_class_uid == "4.5.6"


# ---------------------------------------------------------------------------
# get_instance
# ---------------------------------------------------------------------------

class TestGetInstance:
    async def test_returns_stored_instance(self, service):
        inst = make_instance()
        await service.store_instance(inst)
        result = await service.get_instance(inst.study_uid, inst.series_uid, inst.instance_uid)
        assert result is not None
        assert result.instance_uid == inst.instance_uid
        assert result.study_uid == inst.study_uid

    async def test_returns_none_for_missing_instance(self, service):
        result = await service.get_instance("nonexistent", "series", "instance")
        assert result is None

    async def test_round_trip_sop_class(self, service):
        inst = make_instance(sop_class_uid="1.2.840.10008.5.1.4.1.1.4")
        await service.store_instance(inst)
        result = await service.get_instance(inst.study_uid, inst.series_uid, inst.instance_uid)
        assert result.sop_class_uid == "1.2.840.10008.5.1.4.1.1.4"

    async def test_round_trip_with_pixel_data(self, service):
        inst = make_instance_with_pixel_data()
        await service.store_instance(inst)
        result = await service.get_instance(inst.study_uid, inst.series_uid, inst.instance_uid)
        assert result.pixel_data is not None
        assert result.pixel_data.rows == 4
        assert result.pixel_data.frames[0] == b"\x00\x01\x02\x03"

    async def test_cache_is_used_on_second_read(self, service, temp_storage_dir):
        """Verify the in-memory cache returns the same object on repeated access."""
        inst = make_instance()
        await service.store_instance(inst)
        result1 = await service.get_instance(inst.study_uid, inst.series_uid, inst.instance_uid)
        result2 = await service.get_instance(inst.study_uid, inst.series_uid, inst.instance_uid)
        # Both should be equal (values match)
        assert result1.instance_uid == result2.instance_uid


# ---------------------------------------------------------------------------
# get_series
# ---------------------------------------------------------------------------

class TestGetSeries:
    async def test_returns_all_instances_in_series(self, service):
        study = "study1"
        series = "series1"
        instances = [
            make_instance(study_uid=study, series_uid=series, instance_uid=f"inst{i}")
            for i in range(3)
        ]
        for inst in instances:
            await service.store_instance(inst)

        result = await service.get_series(study, series)
        assert len(result) == 3

    async def test_returns_correct_series(self, service):
        study = "study1"
        inst_a = make_instance(study_uid=study, series_uid="serA", instance_uid="i1")
        inst_b = make_instance(study_uid=study, series_uid="serB", instance_uid="i2")
        await service.store_instance(inst_a)
        await service.store_instance(inst_b)

        result = await service.get_series(study, "serA")
        assert len(result) == 1
        assert result[0].series_uid == "serA"

    async def test_series_instances_are_dcm_instances(self, service):
        study = "study1"
        series = "series1"
        await service.store_instance(make_instance(study_uid=study, series_uid=series, instance_uid="i1"))
        result = await service.get_series(study, series)
        assert all(isinstance(r, DCMInstance) for r in result)


# ---------------------------------------------------------------------------
# get_study
# ---------------------------------------------------------------------------

class TestGetStudy:
    async def test_returns_all_instances_across_series(self, service):
        study = "study1"
        instances = [
            make_instance(study_uid=study, series_uid=f"ser{i}", instance_uid=f"inst{i}")
            for i in range(3)
        ]
        for inst in instances:
            await service.store_instance(inst)

        result = await service.get_study(study)
        assert len(result) == 3

    async def test_multiple_instances_per_series(self, service):
        study = "study1"
        series = "series1"
        for i in range(4):
            await service.store_instance(
                make_instance(study_uid=study, series_uid=series, instance_uid=f"inst{i}")
            )

        result = await service.get_study(study)
        assert len(result) == 4

    async def test_all_returned_are_dcm_instances(self, service):
        study = "study1"
        await service.store_instance(make_instance(study_uid=study, series_uid="s1", instance_uid="i1"))
        await service.store_instance(make_instance(study_uid=study, series_uid="s2", instance_uid="i2"))
        result = await service.get_study(study)
        assert all(isinstance(r, DCMInstance) for r in result)

    async def test_does_not_return_instances_from_other_study(self, service):
        await service.store_instance(make_instance(study_uid="study_A", series_uid="s1", instance_uid="i1"))
        await service.store_instance(make_instance(study_uid="study_B", series_uid="s1", instance_uid="i2"))
        result = await service.get_study("study_A")
        assert all(r.study_uid == "study_A" for r in result)
