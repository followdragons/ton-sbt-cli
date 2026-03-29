from __future__ import annotations

import asyncio
import logging
import string
from pathlib import Path
from typing import Sequence

from pytoniq_core import Address, Cell
from tonutils.clients.http import ToncenterClient
from tonutils.contracts.nft import (
    NFTCollectionBatchMintItemBody,
    NFTCollectionContent,
    NFTCollectionData,
    NFTCollectionMintItemBody,
    NFTCollectionStandard,
    NFTItemSoulbound,
    NFTItemSoulboundMintRef,
    OffchainCommonContent,
    OffchainContent,
    OffchainItemContent,
    RoyaltyParams,
)
from tonutils.utils import to_nano

from ton_sbt_tool.config import ENV_PATH, MAX_BATCH_ITEMS, Settings
from ton_sbt_tool.metadata import get_collection_common_content_url, make_item_suffix
from ton_sbt_tool.wallets import canonical_address, chunked, friendly_address


def load_boc_cell(path: Path) -> Cell:
    if not path.exists():
        raise FileNotFoundError(f"BOC file not found: {path}")

    raw = path.read_bytes()
    if len(raw) >= 4 and raw[:4] == bytes.fromhex("B5EE9C72"):
        return Cell.one_from_boc(raw.hex())

    text = raw.decode("utf-8", errors="ignore").strip()
    if text and all(char in string.hexdigits or char.isspace() for char in text):
        return Cell.one_from_boc("".join(text.split()))

    return Cell.one_from_boc(raw.hex())


def load_collection_code(settings: Settings) -> Cell:
    if settings.collection_code_boc and settings.collection_code_boc.exists():
        logging.info("Using collection code BOC: %s", settings.collection_code_boc)
        return load_boc_cell(settings.collection_code_boc)

    logging.info("Using built-in collection code from tonutils.")
    return NFTCollectionStandard.get_default_code()


def load_sbt_item_code(settings: Settings) -> Cell:
    if settings.item_code_boc and settings.item_code_boc.exists():
        logging.info("Using SBT item code BOC: %s", settings.item_code_boc)
        return load_boc_cell(settings.item_code_boc)

    logging.info("Using built-in SBT item code from tonutils.")
    return NFTItemSoulbound.get_default_code()


def build_collection_contract(
    client: ToncenterClient,
    owner_address: Address,
    settings: Settings,
) -> NFTCollectionStandard:
    collection_code = load_collection_code(settings)
    item_code = load_sbt_item_code(settings)

    content = NFTCollectionContent(
        content=OffchainContent(settings.collection_metadata_url),
        common_content=OffchainCommonContent(get_collection_common_content_url(settings)),
    )
    royalty = RoyaltyParams(royalty=0, denominator=100, address=owner_address)
    data = NFTCollectionData(
        owner_address=owner_address,
        next_item_index=0,
        content=content,
        nft_item_code=item_code,
        royalty_params=royalty,
    )
    return NFTCollectionStandard.from_code_and_data(
        client=client,
        code=collection_code,
        data=data.serialize(),
    )


def build_single_mint_body(
    recipient: Address,
    item_index: int,
    authority_address: Address,
    forward_amount: int,
    settings: Settings,
) -> Cell:
    item_ref = NFTItemSoulboundMintRef(
        owner_address=recipient,
        content=OffchainItemContent(make_item_suffix(settings, item_index)),
        authority_address=authority_address,
        revoked_time=0,
    ).serialize()
    return NFTCollectionMintItemBody(
        item_index=item_index,
        item_ref=item_ref,
        forward_amount=forward_amount,
        query_id=0,
    ).serialize()


def build_batch_mint_body(
    recipients: Sequence[Address],
    start_index: int,
    authority_address: Address,
    forward_amount: int,
    settings: Settings,
) -> Cell:
    refs = [
        NFTItemSoulboundMintRef(
            owner_address=recipient,
            content=OffchainItemContent(
                make_item_suffix(settings, start_index + offset)
            ),
            authority_address=authority_address,
            revoked_time=0,
        ).serialize()
        for offset, recipient in enumerate(recipients)
    ]
    return NFTCollectionBatchMintItemBody(
        items_refs=refs,
        from_index=start_index,
        forward_amount=forward_amount,
        query_id=0,
    ).serialize()


async def send_with_confirmation(
    wallet,
    *,
    destination: Address,
    amount: int,
    body: Cell | None = None,
    state_init=None,
    bounce: bool | None = None,
    settings: Settings,
) -> None:
    await wallet.refresh()
    before_lt = wallet.last_transaction_lt
    before_seqno = None

    if wallet.is_active:
        try:
            before_seqno = await wallet.seqno()
        except Exception:
            before_seqno = None

    await wallet.transfer(
        destination=destination,
        amount=amount,
        body=body,
        state_init=state_init,
        bounce=bounce,
    )

    deadline = asyncio.get_running_loop().time() + settings.send_timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(settings.poll_interval_seconds)
        await wallet.refresh()

        if before_seqno is not None:
            try:
                if await wallet.seqno() != before_seqno:
                    return
            except Exception:
                pass

        if before_lt is None and wallet.last_transaction_lt is not None:
            return

        if before_lt is not None and wallet.last_transaction_lt != before_lt:
            return

    raise TimeoutError(
        f"Wallet transaction was not confirmed within {settings.send_timeout_seconds} seconds."
    )


async def wait_until_active(
    contract,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        await contract.refresh()
        if contract.is_active:
            return
        await asyncio.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Contract {contract.address} did not become active within {timeout_seconds} seconds."
    )


def persist_collection_address(collection_address: str) -> None:
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("COLLECTION_ADDRESS="):
            new_lines.append(f"COLLECTION_ADDRESS={collection_address}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"COLLECTION_ADDRESS={collection_address}")

    ENV_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


async def ensure_collection(
    client: ToncenterClient,
    wallet,
    settings: Settings,
    *,
    deploy_if_missing: bool,
    force_redeploy: bool = False,
) -> NFTCollectionStandard:
    owner_address = wallet.address

    if settings.collection_address:
        collection = NFTCollectionStandard(client, Address(settings.collection_address))
        await collection.refresh()
        if not collection.is_active and not deploy_if_missing:
            raise RuntimeError(
                "COLLECTION_ADDRESS is set but the contract is not active on-chain."
            )
        if collection.is_active:
            collection_data = await collection.get_collection_data()
            owner = collection_data[2]
            if owner is not None and canonical_address(owner) != canonical_address(
                owner_address
            ):
                raise RuntimeError(
                    "Configured COLLECTION_ADDRESS exists, but its owner_address "
                    "does not match the wallet from MNEMONIC."
                )
            logging.info(
                "Using existing collection: %s",
                friendly_address(collection.address, settings.is_testnet),
            )
            return collection

    collection = build_collection_contract(client, owner_address, settings)
    target_address = friendly_address(collection.address, settings.is_testnet)
    await collection.refresh()

    if collection.is_active and not force_redeploy:
        logging.info("Collection already active at %s", target_address)
        persist_collection_address(target_address)
        return collection

    if not deploy_if_missing:
        raise RuntimeError(
            "COLLECTION_ADDRESS is empty and deploy_if_missing is disabled."
        )

    logging.info("Deploying collection to %s", target_address)
    await send_with_confirmation(
        wallet,
        destination=collection.address,
        amount=to_nano(settings.deploy_amount_ton),
        state_init=collection.state_init,
        bounce=False,
        settings=settings,
    )
    await wait_until_active(
        collection,
        timeout_seconds=settings.send_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
    persist_collection_address(target_address)
    logging.info("Collection deployed: %s", target_address)
    return collection


async def verify_minted_item(
    client: ToncenterClient,
    collection: NFTCollectionStandard,
    recipient: Address,
    item_index: int,
    settings: Settings,
) -> None:
    item_address = await collection.get_nft_address_by_index(item_index)
    item = NFTItemSoulbound(client, item_address)
    await wait_until_active(
        item,
        timeout_seconds=settings.send_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    nft_data = await item.get_nft_data()
    owner = nft_data[3]
    if owner is None:
        raise RuntimeError(f"Minted SBT {item_index} has no owner.")

    if canonical_address(owner) != canonical_address(recipient):
        raise RuntimeError(
            f"SBT {item_index} owner mismatch: expected {recipient}, got {owner}"
        )

    authority = await item.get_authority_address()
    logging.info(
        "Verified item %s -> %s | owner=%s | authority=%s",
        item_index,
        friendly_address(item_address, settings.is_testnet),
        friendly_address(owner, settings.is_testnet),
        friendly_address(authority, settings.is_testnet) if authority else "None",
    )


async def mint_recipients(
    client: ToncenterClient,
    wallet,
    collection: NFTCollectionStandard,
    recipients: Sequence[Address],
    settings: Settings,
    *,
    batch_size: int,
    verify: bool,
) -> None:
    if batch_size < 1 or batch_size > MAX_BATCH_ITEMS:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_ITEMS}.")

    await collection.refresh()
    collection_data = await collection.get_collection_data()
    next_item_index = int(collection_data[0])
    owner = collection_data[2]

    if owner is None or canonical_address(owner) != canonical_address(wallet.address):
        raise RuntimeError("Wallet from MNEMONIC is not the collection owner.")

    forward_amount = to_nano(settings.item_forward_amount_ton)
    message_value_per_item = to_nano(settings.mint_message_value_ton)

    logging.info(
        "Starting mint. recipients=%s batch_size=%s next_item_index=%s",
        len(recipients),
        batch_size,
        next_item_index,
    )

    for batch_number, batch in enumerate(chunked(list(recipients), batch_size), start=1):
        start_index = next_item_index
        end_index = start_index + len(batch) - 1

        if len(batch) == 1:
            body = build_single_mint_body(
                recipient=batch[0],
                item_index=start_index,
                authority_address=wallet.address,
                forward_amount=forward_amount,
                settings=settings,
            )
        else:
            body = build_batch_mint_body(
                recipients=batch,
                start_index=start_index,
                authority_address=wallet.address,
                forward_amount=forward_amount,
                settings=settings,
            )

        total_value = message_value_per_item * len(batch)
        logging.info(
            "Sending batch %s | items=%s | index_range=%s..%s | value=%s nanotons",
            batch_number,
            len(batch),
            start_index,
            end_index,
            total_value,
        )

        await send_with_confirmation(
            wallet,
            destination=collection.address,
            amount=total_value,
            body=body,
            bounce=True,
            settings=settings,
        )

        for offset, recipient in enumerate(batch):
            item_index = start_index + offset
            logging.info(
                "Mint submitted | item_index=%s | recipient=%s",
                item_index,
                friendly_address(recipient, settings.is_testnet),
            )
            if verify:
                await verify_minted_item(
                    client=client,
                    collection=collection,
                    recipient=recipient,
                    item_index=item_index,
                    settings=settings,
                )

        next_item_index += len(batch)

    logging.info("Minting completed for %s recipients.", len(recipients))
