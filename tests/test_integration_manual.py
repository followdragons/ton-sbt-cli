from __future__ import annotations

import asyncio
import os

import pytest
from tonutils.clients.http import ToncenterClient
from tonutils.types import DEFAULT_HTTP_RETRY_POLICY, NetworkGlobalID

from ton_sbt_tool import config, minting, wallets


def integration_enabled() -> bool:
    return os.getenv("TON_SBT_RUN_INTEGRATION", "").strip() == "1"


pytestmark = [
    pytest.mark.integration,
    pytest.mark.manual,
    pytest.mark.skipif(
        not integration_enabled(),
        reason="Set TON_SBT_RUN_INTEGRATION=1 to run live testnet integration checks.",
    ),
]


async def _testnet_wallet_and_collection_projection_smoke() -> None:
    settings = config.load_settings()
    if not settings.is_testnet:
        pytest.skip("Integration smoke checks are intended for testnet only.")

    client = ToncenterClient(
        network=NetworkGlobalID.TESTNET,
        api_key=settings.toncenter_api_key,
        base_url=settings.toncenter_endpoint,
        rps_limit=settings.toncenter_rps_limit,
        rps_period=settings.toncenter_rps_period,
        retry_policy=DEFAULT_HTTP_RETRY_POLICY,
    )
    await client.connect()

    try:
        wallet_cls = wallets.wallet_class_for_version(settings.wallet_version)
        wallet, _, _, _ = wallet_cls.from_mnemonic(client, settings.mnemonic)
        await wallet.refresh()

        projected_collection = minting.build_collection_contract(
            client, wallet.address, settings
        )
        await projected_collection.refresh()

        assert wallets.friendly_address(wallet.address, settings.is_testnet)
        assert wallets.friendly_address(
            projected_collection.address, settings.is_testnet
        )
    finally:
        await client.close()


async def _configured_collection_is_queryable_when_present() -> None:
    settings = config.load_settings()
    if not settings.is_testnet:
        pytest.skip("Integration smoke checks are intended for testnet only.")
    if not settings.collection_address:
        pytest.skip("COLLECTION_ADDRESS is empty.")

    client = ToncenterClient(
        network=NetworkGlobalID.TESTNET,
        api_key=settings.toncenter_api_key,
        base_url=settings.toncenter_endpoint,
        rps_limit=settings.toncenter_rps_limit,
        rps_period=settings.toncenter_rps_period,
        retry_policy=DEFAULT_HTTP_RETRY_POLICY,
    )
    await client.connect()

    try:
        wallet_cls = wallets.wallet_class_for_version(settings.wallet_version)
        wallet, _, _, _ = wallet_cls.from_mnemonic(client, settings.mnemonic)
        await wallet.refresh()

        collection = await minting.ensure_collection(
            client=client,
            wallet=wallet,
            settings=settings,
            deploy_if_missing=False,
        )
        await collection.refresh()

        assert wallets.friendly_address(collection.address, settings.is_testnet)
    finally:
        await client.close()


def test_testnet_wallet_and_collection_projection_smoke() -> None:
    asyncio.run(_testnet_wallet_and_collection_projection_smoke())


def test_configured_collection_is_queryable_when_present() -> None:
    asyncio.run(_configured_collection_is_queryable_when_present())
