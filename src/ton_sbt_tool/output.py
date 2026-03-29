from __future__ import annotations

from pathlib import Path
from typing import Sequence

FOLLOWDRAGONS_BANNER = r"""
FFFFFFFF  OOOOO   L        L        OOOOO   W     W
F        O     O  L        L       O     O  W     W
FFFF     O     O  L        L       O     O  W  W  W
F        O     O  L        L       O     O  W W W W
F         OOOOO   LLLLLLL  LLLLLLL  OOOOO    WW WW

DDDDDD   RRRRRR     AAA     GGGGGG   OOOOO   N     N   SSSSSS
D     D  R     R   A   A   G        O     O  NN    N  S
D     D  RRRRRR   AAAAAAA  G  GGGG  O     O  N N   N   SSSSS
D     D  R   R    A     A  G     G  O     O  N  N  N       S
DDDDDD   R    RR  A     A   GGGGGG   OOOOO   N   NNN  SSSSSS
"""


def print_banner() -> None:
    print(FOLLOWDRAGONS_BANNER)


def print_next_steps(title: str, steps: Sequence[str]) -> None:
    print("")
    print(f"[{title}]")
    for step in steps:
        print(step)


def print_wallet_new_guidance(out_path: Path) -> None:
    print_next_steps(
        "Next",
        [
            f"1. Open {out_path}",
            "2. Copy `MNEMONIC=` and `WALLET_VERSION=` into `.env`",
            "3. Leave `COLLECTION_ADDRESS=` empty for the first deploy",
            "4. Fund the printed testnet address with test TON",
            "5. Run `.\\scripts\\run.ps1 doctor --wallets wallets.txt`",
        ],
    )


def print_wallets_generate_guidance(txt_path: Path) -> None:
    print_next_steps(
        "Next",
        [
            f"1. Use `{txt_path}` as your recipient list",
            "2. Optionally copy it to `wallets.txt`",
            "3. Run `.\\scripts\\run.ps1 doctor --wallets <that file>`",
            "4. Then run `.\\scripts\\run.ps1 run --wallets <that file>`",
        ],
    )


def print_doctor_guidance(wallets_path: Path) -> None:
    print_next_steps(
        "Next",
        [
            "1. If wallet balance is enough, proceed to deploy/mint",
            f"2. Run `.\\scripts\\run.ps1 run --wallets {wallets_path}`",
            "3. If you only want deploy, run `.\\scripts\\run.ps1 deploy`",
        ],
    )


def print_deploy_guidance(collection_address: str) -> None:
    print_next_steps(
        "Next",
        [
            f"1. Collection is ready at `{collection_address}`",
            "2. Confirm `COLLECTION_ADDRESS=` was written to `.env`",
            "3. Put your recipient file in the project root as `wallets.txt`, or keep it anywhere and pass its path with `--wallets`",
            "4. Store one TON address per line in that file",
            "5. Run `.\\scripts\\run.ps1 mint --wallets wallets.txt`",
        ],
    )


def print_run_guidance(collection_address: str) -> None:
    print_next_steps(
        "Next",
        [
            f"1. Reuse collection `{collection_address}` for future mint runs",
            "2. Add new addresses into another wallet list file",
            "3. Run `.\\scripts\\run.ps1 mint --wallets <new file>`",
            "4. Swap metadata URLs in `.env` when moving from test to production",
        ],
    )
