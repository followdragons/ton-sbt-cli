from pathlib import Path

import pytest

from ton_sbt_tool import minting, wallets


def test_load_wallet_addresses_ignores_comments_blanks_and_duplicates(
    tmp_path: Path,
) -> None:
    wallets_file = tmp_path / "wallets.txt"
    wallets_file.write_text(
        "\n".join(
                [
                    "# comment",
                    "",
                    "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c",
                    "EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c",
                    "kQBBYzw3-N7wle1V7KJJv9yQopTB_iNuEX93e8UgUFsIGQGf",
                ]
            )
            + "\n",
            encoding="utf-8",
    )

    addresses = wallets.load_wallet_addresses(wallets_file)

    assert len(addresses) == 2
    assert wallets.canonical_address(addresses[0]) != wallets.canonical_address(addresses[1])


def test_load_wallet_addresses_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        wallets.load_wallet_addresses(tmp_path / "missing.txt")


def test_load_wallet_addresses_requires_at_least_one_address(tmp_path: Path) -> None:
    wallets_file = tmp_path / "wallets.txt"
    wallets_file.write_text("# only comments\n\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No wallet addresses found"):
        wallets.load_wallet_addresses(wallets_file)


def test_persist_collection_address_updates_existing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "MNEMONIC=test\nCOLLECTION_ADDRESS=\nIS_TESTNET=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(minting, "ENV_PATH", env_path)

    minting.persist_collection_address("EQCcollectionaddress")

    text = env_path.read_text(encoding="utf-8")
    assert "COLLECTION_ADDRESS=EQCcollectionaddress" in text
    assert text.count("COLLECTION_ADDRESS=") == 1


def test_persist_collection_address_appends_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("MNEMONIC=test\nIS_TESTNET=true\n", encoding="utf-8")
    monkeypatch.setattr(minting, "ENV_PATH", env_path)

    minting.persist_collection_address("EQCcollectionaddress")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    assert lines[-1] == "COLLECTION_ADDRESS=EQCcollectionaddress"
