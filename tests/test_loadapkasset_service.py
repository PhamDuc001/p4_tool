from processes import loadapkasset_process
from services.loadapkasset_service import LoadApkAssetService


def sample_readahead_manager():
    return """public class ReadaheadManager {
    private void initModel() {
        if (PerformanceFeature.CHIP_EXYNOS850) {
            mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_CLOCK);
        }
    }
}
"""


def test_add_assets_to_chipset_content_appends_missing_assets():
    content, changed, assets_to_add = loadapkasset_process.add_assets_to_chipset_content(
        sample_readahead_manager(),
        "EXYNOS850",
        ["ASSET_GALLERY", "ASSET_CLOCK", "ASSET_GALLERY"],
    )

    assert changed is True
    assert assets_to_add == ["ASSET_GALLERY"]
    assert "mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_CLOCK | ASSET_GALLERY)" in content


def test_add_assets_to_chipset_content_returns_unchanged_for_existing_assets():
    original = sample_readahead_manager()

    content, changed, assets_to_add = loadapkasset_process.add_assets_to_chipset_content(
        original,
        "EXYNOS850",
        ["ASSET_CAMERA"],
    )

    assert changed is False
    assert assets_to_add == []
    assert content == original


def test_loadapkasset_service_preview_returns_diff_without_writing_file(tmp_path):
    target = tmp_path / "ReadaheadManager.java"
    target.write_text(sample_readahead_manager(), encoding="utf-8")

    service = LoadApkAssetService(
        depot_to_local_path_fn=lambda depot_path: str(target),
    )

    result = service.preview_add_assets(
        "//depot/vendor/samsung/ReadaheadManager.java",
        "EXYNOS850",
        ["ASSET_GALLERY"],
        log_callback=lambda message: None,
    )

    assert result.success is True
    assert result.changed_files == ["//depot/vendor/samsung/ReadaheadManager.java"]
    assert result.details["assets_to_add"] == ["ASSET_GALLERY"]
    assert result.details["preview"].changed is True
    assert "ASSET_GALLERY" in result.details["preview"].diff
    assert target.read_text(encoding="utf-8") == sample_readahead_manager()
