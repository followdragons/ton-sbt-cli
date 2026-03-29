from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

TESTNET_ENDPOINT = "https://testnet.toncenter.com/api/v2"
MAINNET_ENDPOINT = "https://toncenter.com/api/v2"
MAX_BATCH_ITEMS = 249
ENV_PATH = Path(".env")
GENERATED_WALLETS_DIR = Path("generated_wallets")


@dataclass
class Settings:
    mnemonic: list[str]
    wallet_version: str
    collection_address: str | None
    collection_metadata_url: str
    items_base_url: str
    item_metadata_suffix: str | None
    is_testnet: bool
    toncenter_api_key: str | None
    toncenter_endpoint: str
    toncenter_rps_limit: int
    toncenter_rps_period: float
    collection_code_boc: Path | None
    item_code_boc: Path | None
    deploy_amount_ton: str
    mint_message_value_ton: str
    item_forward_amount_ton: str
    default_batch_size: int
    verify_mints: bool
    send_timeout_seconds: float
    poll_interval_seconds: float


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def normalize_toncenter_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.endswith("/jsonRPC"):
        endpoint = endpoint[: -len("/jsonRPC")]
    return endpoint


def load_settings() -> Settings:
    load_dotenv(override=False)

    mnemonic_raw = require_env("MNEMONIC")
    mnemonic = [word for word in mnemonic_raw.split() if word]
    if len(mnemonic) != 24:
        raise ValueError("MNEMONIC must contain exactly 24 words.")

    is_testnet = parse_bool(os.getenv("IS_TESTNET"), default=True)
    endpoint = os.getenv("TONCENTER_ENDPOINT", "").strip()
    if not endpoint:
        endpoint = TESTNET_ENDPOINT if is_testnet else MAINNET_ENDPOINT
    endpoint = normalize_toncenter_endpoint(endpoint)

    settings = Settings(
        mnemonic=mnemonic,
        wallet_version=os.getenv("WALLET_VERSION", "v4r2").strip().lower(),
        collection_address=os.getenv("COLLECTION_ADDRESS", "").strip() or None,
        collection_metadata_url=require_env("COLLECTION_METADATA_URL"),
        items_base_url=require_env("ITEMS_BASE_URL"),
        item_metadata_suffix=os.getenv("ITEM_METADATA_SUFFIX", "").strip() or None,
        is_testnet=is_testnet,
        toncenter_api_key=os.getenv("TONCENTER_API_KEY", "").strip() or None,
        toncenter_endpoint=endpoint,
        toncenter_rps_limit=int(os.getenv("TONCENTER_RPS_LIMIT", "1").strip()),
        toncenter_rps_period=float(os.getenv("TONCENTER_RPS_PERIOD", "1.0").strip()),
        collection_code_boc=(
            Path(value)
            if (value := os.getenv("SBT_COLLECTION_CODE_BOC", "").strip())
            else None
        ),
        item_code_boc=(
            Path(value)
            if (value := os.getenv("SBT_ITEM_CODE_BOC", "").strip())
            else None
        ),
        deploy_amount_ton=os.getenv("DEPLOY_AMOUNT_TON", "0.05").strip(),
        mint_message_value_ton=os.getenv("MINT_MESSAGE_VALUE_TON", "0.02").strip(),
        item_forward_amount_ton=os.getenv("ITEM_FORWARD_AMOUNT_TON", "0.005").strip(),
        default_batch_size=int(os.getenv("BATCH_SIZE", "50").strip()),
        verify_mints=parse_bool(os.getenv("VERIFY_MINTS"), default=True),
        send_timeout_seconds=float(os.getenv("SEND_TIMEOUT_SECONDS", "90").strip()),
        poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", "2.0").strip()),
    )

    if settings.default_batch_size < 1 or settings.default_batch_size > MAX_BATCH_ITEMS:
        raise ValueError(f"BATCH_SIZE must be between 1 and {MAX_BATCH_ITEMS}.")

    if settings.wallet_version not in {"v4r2", "v5r1"}:
        raise ValueError("WALLET_VERSION must be either `v4r2` or `v5r1`.")

    return settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ton-sbt-cli",
        description="Deploy TON SBT collection and batch-mint SBTs.",
        epilog="FOLLOW / DRAGONS CLI: wallet-new -> doctor -> run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy", help="Deploy collection only.")
    deploy_parser.add_argument(
        "--force-redeploy",
        action="store_true",
        help="Send deploy even if the computed address already exists and is active.",
    )

    wallet_new_parser = subparsers.add_parser(
        "wallet-new",
        help="Generate one new wallet for collection ownership or manual use.",
    )
    wallet_new_parser.add_argument(
        "--wallet-version",
        default="v4r2",
        choices=["v4r2", "v5r1"],
        help="Wallet contract version.",
    )
    wallet_new_parser.add_argument(
        "--words",
        type=int,
        default=24,
        choices=[12, 18, 24],
        help="Mnemonic word count.",
    )
    wallet_new_parser.add_argument(
        "--out-dir",
        default=str(GENERATED_WALLETS_DIR),
        help="Directory where generated wallet files will be stored.",
    )
    wallet_new_parser.add_argument(
        "--label",
        default="collection-owner",
        help="Label prefix for output filename.",
    )

    wallets_generate_parser = subparsers.add_parser(
        "wallets-generate",
        help="Generate multiple test wallets and save full data plus address list.",
    )
    wallets_generate_parser.add_argument(
        "--wallet-version",
        default="v4r2",
        choices=["v4r2", "v5r1"],
        help="Wallet contract version.",
    )
    wallets_generate_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="How many wallets to generate.",
    )
    wallets_generate_parser.add_argument(
        "--words",
        type=int,
        default=24,
        choices=[12, 18, 24],
        help="Mnemonic word count.",
    )
    wallets_generate_parser.add_argument(
        "--out-dir",
        default=str(GENERATED_WALLETS_DIR),
        help="Directory where generated wallet files will be stored.",
    )
    wallets_generate_parser.add_argument(
        "--label",
        default="test-wallets",
        help="Label prefix for output filenames.",
    )
    wallets_generate_parser.add_argument(
        "--addresses-out",
        default=None,
        help="Optional custom path for the generated recipient address list.",
    )

    doctor_parser = subparsers.add_parser(
        "doctor", help="Validate config, wallet, recipients, and collection state."
    )
    doctor_parser.add_argument(
        "--wallets",
        default="wallets.txt",
        help="Path to recipient wallet list.",
    )

    mint_parser = subparsers.add_parser("mint", help="Mint to recipients only.")
    mint_parser.add_argument(
        "--wallets",
        default="wallets.txt",
        help="Path to recipient wallet list.",
    )
    mint_parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Batch size, max {MAX_BATCH_ITEMS}.",
    )
    mint_parser.add_argument(
        "--verify",
        dest="verify",
        action="store_true",
        default=None,
        help="Verify minted items on-chain.",
    )
    mint_parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip on-chain verification.",
    )

    run_parser = subparsers.add_parser(
        "run", help="Deploy if needed, then batch-mint recipients."
    )
    run_parser.add_argument(
        "--wallets",
        default="wallets.txt",
        help="Path to recipient wallet list.",
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Batch size, max {MAX_BATCH_ITEMS}.",
    )
    run_parser.add_argument(
        "--verify",
        dest="verify",
        action="store_true",
        default=None,
        help="Verify minted items on-chain.",
    )
    run_parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip on-chain verification.",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()
