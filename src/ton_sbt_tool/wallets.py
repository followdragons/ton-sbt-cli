from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from pytoniq_core import Address
from tonutils.clients.http import ToncenterClient
from tonutils.contracts.wallet import WalletV4R2, WalletV5R1
from tonutils.types import NetworkGlobalID

from ton_sbt_tool.output import (
    print_banner,
    print_wallet_new_guidance,
    print_wallets_generate_guidance,
)


def wallet_class_for_version(version: str):
    if version == "v5r1":
        return WalletV5R1
    return WalletV4R2


def friendly_address(address: Address, is_testnet: bool) -> str:
    return address.to_str(
        is_user_friendly=True,
        is_url_safe=True,
        is_bounceable=True,
        is_test_only=is_testnet,
    )


def canonical_address(address: Address) -> str:
    return address.to_str(
        is_user_friendly=False,
        is_url_safe=True,
        is_bounceable=True,
        is_test_only=False,
    )


def from_nano(value: int) -> str:
    whole = value // 10**9
    frac = value % 10**9
    if frac == 0:
        return str(whole)
    return f"{whole}.{frac:09d}".rstrip("0")


def load_wallet_addresses(path: Path) -> list[Address]:
    if not path.exists():
        raise FileNotFoundError(f"Wallet list file not found: {path}")

    recipients: list[Address] = []
    seen: set[str] = set()

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        address = Address(line)
        key = canonical_address(address)
        if key in seen:
            logging.warning("Skipping duplicate recipient: %s", line)
            continue

        seen.add(key)
        recipients.append(address)

    if not recipients:
        raise ValueError(f"No wallet addresses found in {path}")

    return recipients


def chunked(values: Sequence[Address], size: int) -> Iterable[list[Address]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def now_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def make_wallet_payload(
    wallet,
    public_key,
    private_key,
    mnemonic: Sequence[str],
    wallet_version: str,
) -> dict:
    testnet_address = wallet.address.to_str(
        is_user_friendly=True,
        is_url_safe=True,
        is_bounceable=True,
        is_test_only=True,
    )
    mainnet_address = wallet.address.to_str(
        is_user_friendly=True,
        is_url_safe=True,
        is_bounceable=True,
        is_test_only=False,
    )
    raw_address = wallet.address.to_str(is_user_friendly=False)
    phrase = " ".join(mnemonic)
    return {
        "wallet_version": wallet_version,
        "mnemonic_words": list(mnemonic),
        "mnemonic": phrase,
        "raw_address": raw_address,
        "testnet_address": testnet_address,
        "mainnet_address": mainnet_address,
        "public_key_hex": public_key.as_hex,
        "private_key_hex": private_key.as_hex,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "env_hint": {
            "MNEMONIC": phrase,
            "WALLET_VERSION": wallet_version,
            "COLLECTION_ADDRESS": "",
            "IS_TESTNET": "true",
        },
    }


def generate_wallet(
    *,
    wallet_version: str,
    mnemonic_length: int,
) -> dict:
    client = ToncenterClient(network=NetworkGlobalID.TESTNET)
    wallet_cls = wallet_class_for_version(wallet_version)
    wallet, public_key, private_key, mnemonic = wallet_cls.create(
        client=client,
        mnemonic_length=mnemonic_length,
    )
    payload = make_wallet_payload(
        wallet,
        public_key,
        private_key,
        mnemonic,
        wallet_version,
    )
    payload["wallet_version"] = wallet_cls.__name__
    return payload


def run_wallet_new(
    *,
    wallet_version: str,
    mnemonic_length: int,
    out_dir: Path,
    label: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = generate_wallet(
        wallet_version=wallet_version,
        mnemonic_length=mnemonic_length,
    )
    out_path = out_dir / f"{label}-{now_timestamp()}.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print_banner()
    print(f"Saved wallet data to: {out_path}")
    print("")
    print("MNEMONIC=" + payload["mnemonic"])
    print("WALLET_VERSION=" + wallet_version)
    print("COLLECTION_ADDRESS=")
    print("IS_TESTNET=true")
    print("")
    print("Testnet address: " + payload["testnet_address"])
    print("Mainnet address: " + payload["mainnet_address"])
    print("Raw address: " + payload["raw_address"])
    print_wallet_new_guidance(out_path)


def run_wallets_generate(
    *,
    count: int,
    wallet_version: str,
    mnemonic_length: int,
    out_dir: Path,
    label: str,
    addresses_out: Path | None,
) -> None:
    if count < 1:
        raise ValueError("count must be at least 1.")

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_timestamp()
    json_path = out_dir / f"{label}-{timestamp}.json"
    txt_path = addresses_out or out_dir / f"{label}-{timestamp}.txt"

    wallets: list[dict] = []
    addresses: list[str] = []
    for index in range(1, count + 1):
        payload = generate_wallet(
            wallet_version=wallet_version,
            mnemonic_length=mnemonic_length,
        )
        payload["index"] = index
        wallets.append(payload)
        addresses.append(payload["testnet_address"])

    batch_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_hint": "testnet",
        "count": count,
        "wallets": wallets,
    }
    json_path.write_text(
        json.dumps(batch_payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    txt_path.write_text("\n".join(addresses) + "\n", encoding="utf-8")

    print_banner()
    print(f"Saved wallet batch to: {json_path}")
    print(f"Saved address list to: {txt_path}")
    print("")
    for address in addresses:
        print(address)
    print_wallets_generate_guidance(txt_path)
