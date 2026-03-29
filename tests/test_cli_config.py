from pathlib import Path

import pytest

from ton_sbt_tool import config


def base_env() -> dict[str, str]:
    return {
        "MNEMONIC": "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 "
        "word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24",
        "WALLET_VERSION": "v5r1",
        "COLLECTION_ADDRESS": "",
        "COLLECTION_METADATA_URL": "https://example.com/collection.json",
        "ITEMS_BASE_URL": "https://example.com/metadata/",
        "ITEM_METADATA_SUFFIX": "",
        "IS_TESTNET": "true",
        "TONCENTER_API_KEY": "",
        "TONCENTER_ENDPOINT": "",
        "TONCENTER_RPS_LIMIT": "1",
        "TONCENTER_RPS_PERIOD": "1.0",
        "DEPLOY_AMOUNT_TON": "0.05",
        "MINT_MESSAGE_VALUE_TON": "0.02",
        "ITEM_FORWARD_AMOUNT_TON": "0.005",
        "BATCH_SIZE": "50",
        "VERIFY_MINTS": "true",
        "SEND_TIMEOUT_SECONDS": "90",
        "POLL_INTERVAL_SECONDS": "2.0",
    }


def apply_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_load_settings_uses_defaults_and_normalizes_endpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    apply_env(monkeypatch, base_env())

    settings = config.load_settings()

    assert settings.wallet_version == "v5r1"
    assert settings.collection_address is None
    assert settings.is_testnet is True
    assert settings.toncenter_endpoint == config.TESTNET_ENDPOINT
    assert settings.default_batch_size == 50
    assert settings.verify_mints is True


def test_load_settings_respects_mainnet_and_jsonrpc_suffix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    values = base_env()
    values["IS_TESTNET"] = "false"
    values["TONCENTER_ENDPOINT"] = "https://toncenter.com/api/v2/jsonRPC"
    apply_env(monkeypatch, values)

    settings = config.load_settings()

    assert settings.is_testnet is False
    assert settings.toncenter_endpoint == config.MAINNET_ENDPOINT


def test_load_settings_rejects_bad_mnemonic_length(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    values = base_env()
    values["MNEMONIC"] = "too short"
    apply_env(monkeypatch, values)

    with pytest.raises(ValueError, match="exactly 24 words"):
        config.load_settings()


def test_load_settings_rejects_invalid_batch_size(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    values = base_env()
    values["BATCH_SIZE"] = "250"
    apply_env(monkeypatch, values)

    with pytest.raises(ValueError, match="BATCH_SIZE must be between 1 and 249"):
        config.load_settings()


def test_parse_bool_variants() -> None:
    assert config.parse_bool("true") is True
    assert config.parse_bool("YES") is True
    assert config.parse_bool("1") is True
    assert config.parse_bool("off") is False
    assert config.parse_bool(None, default=True) is True


def test_normalize_toncenter_endpoint() -> None:
    assert (
        config.normalize_toncenter_endpoint(
            "https://testnet.toncenter.com/api/v2/jsonRPC"
        )
        == config.TESTNET_ENDPOINT
    )
    assert (
        config.normalize_toncenter_endpoint("https://toncenter.com/api/v2/")
        == config.MAINNET_ENDPOINT
    )
