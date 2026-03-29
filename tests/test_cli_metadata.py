from dataclasses import replace

from ton_sbt_tool import config, metadata


def make_settings(**overrides):
    settings = config.Settings(
        mnemonic=["word"] * 24,
        wallet_version="v5r1",
        collection_address=None,
        collection_metadata_url="https://example.com/collection.json",
        items_base_url="https://example.com/metadata/",
        item_metadata_suffix=None,
        is_testnet=True,
        toncenter_api_key=None,
        toncenter_endpoint=config.TESTNET_ENDPOINT,
        toncenter_rps_limit=1,
        toncenter_rps_period=1.0,
        collection_code_boc=None,
        item_code_boc=None,
        deploy_amount_ton="0.05",
        mint_message_value_ton="0.02",
        item_forward_amount_ton="0.005",
        default_batch_size=50,
        verify_mints=True,
        send_timeout_seconds=90.0,
        poll_interval_seconds=2.0,
    )
    return replace(settings, **overrides)


def test_items_base_url_prefix_mode_detected() -> None:
    settings = make_settings(items_base_url="https://example.com/metadata/")

    assert metadata.is_fixed_item_metadata_url(settings.items_base_url) is False
    assert metadata.get_item_metadata_mode(settings) == "prefix"
    assert metadata.get_collection_common_content_url(settings) == settings.items_base_url


def test_items_base_url_fixed_file_mode_detected() -> None:
    settings = make_settings(items_base_url="https://example.com/metadata/176.json")

    assert metadata.is_fixed_item_metadata_url(settings.items_base_url) is True
    assert metadata.get_item_metadata_mode(settings) == "fixed-file"
    assert metadata.get_collection_common_content_url(settings) == ""


def test_make_item_suffix_uses_index_json_by_default() -> None:
    settings = make_settings()

    assert metadata.make_item_suffix(settings, 0) == "0.json"
    assert metadata.make_item_suffix(settings, 7) == "7.json"


def test_make_item_suffix_uses_fixed_suffix_in_prefix_mode() -> None:
    settings = make_settings(item_metadata_suffix="176.json")

    assert metadata.make_item_suffix(settings, 0) == "176.json"
    assert metadata.make_item_suffix(settings, 5) == "176.json"


def test_make_item_suffix_uses_full_file_url_in_fixed_file_mode() -> None:
    settings = make_settings(
        items_base_url="https://example.com/metadata/176.json",
        item_metadata_suffix="ignored.json",
    )

    assert (
        metadata.make_item_suffix(settings, 0)
        == "https://example.com/metadata/176.json"
    )
    assert (
        metadata.make_item_suffix(settings, 9)
        == "https://example.com/metadata/176.json"
    )
