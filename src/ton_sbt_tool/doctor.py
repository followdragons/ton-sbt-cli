from __future__ import annotations

import logging
from pathlib import Path

from pytoniq_core import Address
from tonutils.clients.http import ToncenterClient
from tonutils.contracts.nft import NFTCollectionStandard
from tonutils.utils import to_nano

from ton_sbt_tool.config import Settings
from ton_sbt_tool.metadata import get_item_metadata_mode
from ton_sbt_tool.minting import (
    build_collection_contract,
    load_collection_code,
    load_sbt_item_code,
)
from ton_sbt_tool.wallets import (
    canonical_address,
    friendly_address,
    from_nano,
    load_wallet_addresses,
)


async def run_doctor(
    client: ToncenterClient,
    wallet,
    settings: Settings,
    *,
    wallets_path: Path,
) -> None:
    logging.info("Doctor: validating local configuration")
    logging.info("Network: %s", "testnet" if settings.is_testnet else "mainnet")
    logging.info("Toncenter endpoint: %s", settings.toncenter_endpoint)
    metadata_mode = get_item_metadata_mode(settings)
    logging.info("Item metadata mode: %s", metadata_mode)
    if metadata_mode == "fixed-file":
        logging.info(
            "Every minted SBT will point to the same metadata file: %s",
            settings.items_base_url,
        )
        if settings.item_metadata_suffix:
            logging.warning(
                "ITEM_METADATA_SUFFIX is ignored because ITEMS_BASE_URL is a concrete file URL."
            )
    else:
        logging.info("Item metadata base URL: %s", settings.items_base_url)
        if settings.item_metadata_suffix:
            logging.info(
                "All minted SBTs will use the fixed suffix: %s",
                settings.item_metadata_suffix,
            )
        else:
            logging.info(
                "Per-item metadata will be generated as <item_index>.json under ITEMS_BASE_URL."
            )

    recipients: list[Address] = []
    if wallets_path.exists():
        recipients = load_wallet_addresses(wallets_path)
        logging.info("Recipients file: %s", wallets_path)
        logging.info("Recipients loaded: %s", len(recipients))
    else:
        logging.warning("Recipients file not found: %s", wallets_path)

    collection_code = load_collection_code(settings)
    item_code = load_sbt_item_code(settings)
    logging.info("Collection code hash: %s", collection_code.hash.hex())
    logging.info("SBT item code hash: %s", item_code.hash.hex())

    await wallet.refresh()
    logging.info(
        "Owner wallet: %s",
        friendly_address(wallet.address, settings.is_testnet),
    )
    logging.info("Wallet state: %s", wallet.state.value)
    logging.info("Wallet balance: %s TON", from_nano(wallet.balance))
    if wallet.is_active:
        logging.info("Wallet seqno: %s", await wallet.seqno())
    else:
        logging.warning("Wallet is not active on-chain yet.")

    projected_collection = build_collection_contract(client, wallet.address, settings)
    logging.info(
        "Projected collection address: %s",
        friendly_address(projected_collection.address, settings.is_testnet),
    )

    deploy_amount = to_nano(settings.deploy_amount_ton)
    mint_amount = to_nano(settings.mint_message_value_ton)
    estimated_total = mint_amount * len(recipients)
    if not settings.collection_address:
        estimated_total += deploy_amount

    logging.info("Configured deploy amount: %s TON", settings.deploy_amount_ton)
    logging.info(
        "Configured per-item mint message value: %s TON",
        settings.mint_message_value_ton,
    )
    logging.info(
        "Configured item forward amount: %s TON",
        settings.item_forward_amount_ton,
    )
    logging.info(
        "Estimated minimum total for current run shape: %s TON plus fees",
        from_nano(estimated_total),
    )

    if wallet.balance < estimated_total:
        logging.warning(
            "Wallet balance looks lower than estimated deploy/mint value requirement."
        )

    if settings.collection_address:
        collection = NFTCollectionStandard(client, Address(settings.collection_address))
        await collection.refresh()
        logging.info(
            "Configured collection address: %s",
            friendly_address(collection.address, settings.is_testnet),
        )
        logging.info("Collection state: %s", collection.state.value)
        if collection.is_active:
            collection_data = await collection.get_collection_data()
            owner = collection_data[2]
            logging.info("Collection next_item_index: %s", int(collection_data[0]))
            logging.info(
                "Collection owner: %s",
                friendly_address(owner, settings.is_testnet) if owner else "None",
            )
            if owner and canonical_address(owner) != canonical_address(wallet.address):
                raise RuntimeError(
                    "COLLECTION_ADDRESS exists, but owner_address does not match MNEMONIC wallet."
                )
        else:
            logging.warning("Configured collection address is not active on-chain.")
    else:
        logging.info(
            "COLLECTION_ADDRESS is empty. This is correct for the first deploy."
        )
        logging.info(
            "After `deploy` or `run`, the script will write COLLECTION_ADDRESS to .env automatically."
        )

    logging.info("Doctor completed successfully.")
