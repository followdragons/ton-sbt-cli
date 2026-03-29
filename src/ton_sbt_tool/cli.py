from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from tonutils.clients.http import ToncenterClient
from tonutils.types import DEFAULT_HTTP_RETRY_POLICY, NetworkGlobalID

from ton_sbt_tool.config import (
    ENV_PATH,
    GENERATED_WALLETS_DIR,
    MAINNET_ENDPOINT,
    MAX_BATCH_ITEMS,
    TESTNET_ENDPOINT,
    Settings,
    load_settings,
    normalize_toncenter_endpoint,
    parse_args,
    parse_bool,
    require_env,
    setup_logging,
)
from ton_sbt_tool.doctor import run_doctor
from ton_sbt_tool.metadata import (
    get_collection_common_content_url,
    get_item_metadata_mode,
    is_fixed_item_metadata_url,
    make_item_suffix,
)
from ton_sbt_tool.minting import (
    build_batch_mint_body,
    build_collection_contract,
    build_single_mint_body,
    ensure_collection,
    load_boc_cell,
    load_collection_code,
    load_sbt_item_code,
    mint_recipients,
    persist_collection_address,
    send_with_confirmation,
    verify_minted_item,
    wait_until_active,
)
from ton_sbt_tool.output import (
    FOLLOWDRAGONS_BANNER,
    print_banner,
    print_deploy_guidance,
    print_doctor_guidance,
    print_next_steps,
    print_run_guidance,
)
from ton_sbt_tool.wallets import (
    canonical_address,
    chunked,
    friendly_address,
    from_nano,
    generate_wallet,
    load_wallet_addresses,
    now_timestamp,
    run_wallet_new,
    run_wallets_generate,
    wallet_class_for_version,
)


async def main_async() -> None:
    setup_logging()
    args = parse_args()
    print_banner()

    if args.command == "wallet-new":
        run_wallet_new(
            wallet_version=args.wallet_version,
            mnemonic_length=args.words,
            out_dir=Path(args.out_dir),
            label=args.label,
        )
        return

    if args.command == "wallets-generate":
        run_wallets_generate(
            count=args.count,
            wallet_version=args.wallet_version,
            mnemonic_length=args.words,
            out_dir=Path(args.out_dir),
            label=args.label,
            addresses_out=Path(args.addresses_out) if args.addresses_out else None,
        )
        return

    settings = load_settings()

    network = (
        NetworkGlobalID.TESTNET if settings.is_testnet else NetworkGlobalID.MAINNET
    )
    client = ToncenterClient(
        network=network,
        api_key=settings.toncenter_api_key,
        base_url=settings.toncenter_endpoint,
        rps_limit=settings.toncenter_rps_limit,
        rps_period=settings.toncenter_rps_period,
        retry_policy=DEFAULT_HTTP_RETRY_POLICY,
    )
    await client.connect()

    try:
        wallet_cls = wallet_class_for_version(settings.wallet_version)
        wallet, _, _, _ = wallet_cls.from_mnemonic(client, settings.mnemonic)
        logging.info(
            "Owner wallet (%s): %s",
            settings.wallet_version,
            friendly_address(wallet.address, settings.is_testnet),
        )

        if args.command == "doctor":
            await run_doctor(
                client=client,
                wallet=wallet,
                settings=settings,
                wallets_path=Path(args.wallets),
            )
            print_doctor_guidance(Path(args.wallets))
            return

        if args.command == "deploy":
            collection = await ensure_collection(
                client=client,
                wallet=wallet,
                settings=settings,
                deploy_if_missing=True,
                force_redeploy=args.force_redeploy,
            )
            logging.info(
                "Collection ready: %s",
                friendly_address(collection.address, settings.is_testnet),
            )
            print_deploy_guidance(
                friendly_address(collection.address, settings.is_testnet)
            )
            return

        verify = settings.verify_mints if args.verify is None else args.verify
        batch_size = args.batch_size or settings.default_batch_size
        wallets_path = Path(args.wallets)
        recipients = load_wallet_addresses(wallets_path)

        deploy_if_missing = args.command == "run"
        if args.command == "mint" and not settings.collection_address:
            raise RuntimeError(
                "COLLECTION_ADDRESS is empty. Use `run` to deploy automatically or set COLLECTION_ADDRESS in .env."
            )

        collection = await ensure_collection(
            client=client,
            wallet=wallet,
            settings=settings,
            deploy_if_missing=deploy_if_missing,
        )

        await mint_recipients(
            client=client,
            wallet=wallet,
            collection=collection,
            recipients=recipients,
            settings=settings,
            batch_size=batch_size,
            verify=verify,
        )
        if args.command == "mint":
            print_next_steps(
                "Next",
                [
                    "1. Check newly minted items on-chain or in your explorer",
                    "2. For another recipient batch, run `.\\scripts\\run.ps1 mint --wallets <new file>`",
                    "3. Keep the current `COLLECTION_ADDRESS` in `.env`",
                ],
            )
        if args.command == "run":
            print_run_guidance(
                friendly_address(collection.address, settings.is_testnet)
            )
    finally:
        await client.close()


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        logging.error("%s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
