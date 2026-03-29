# TON SBT CLI

```text
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
```

This project is a Python CLI application for TON SBT collection deployment and minting.

It provides an end-to-end command-line workflow for:

- creating an owner wallet
- generating recipient wallets
- validating configuration and balances before sending transactions
- deploying an SBT collection
- batch minting SBTs
- verifying minted items on-chain

This tool is intended to support two distinct workflows:

- testnet validation, where you can create throwaway wallets and verify the full deploy/mint flow safely
- mainnet execution, where you should use a real owner wallet and a real recipient list supplied by the end user or your production process

The project is fully open source and implemented by FollowDragons, 2026.

## Final Project Structure

```text
.
|-- .env
|-- .env.example
|-- .gitignore
|-- LICENSE
|-- README.md
|-- pyproject.toml
|-- contracts/
|   `-- README.md
|-- generated_wallets/
|-- scripts/
|   |-- new-wallet.ps1
|   |-- run.ps1
|   |-- setup.ps1
|   `-- test.ps1
|-- src/
|   `-- ton_sbt_tool/
|       |-- __init__.py
|       |-- __main__.py
|       |-- cli.py
|       |-- config.py
|       |-- doctor.py
|       |-- metadata.py
|       |-- minting.py
|       |-- output.py
|       `-- wallets.py
|-- tests/
|   |-- test_cli_config.py
|   |-- test_cli_files.py
|   |-- test_cli_metadata.py
|   `-- test_integration_manual.py
`-- wallets.txt.example
```

There are no legacy root-level Python launchers in the final layout.
The supported entrypoints are the PowerShell scripts, the installed console script, and the Python module entrypoint.

## Entry Points

Main PowerShell entrypoint:

```powershell
.\scripts\run.ps1 <command> [options]
```

Installed console script entrypoint:

```powershell
.\.venv\Scripts\ton-sbt-cli <command> [options]
```

Direct Python module entrypoint:

```powershell
.\.venv\Scripts\python -m ton_sbt_tool <command> [options]
```

## Installation

Install the project in editable mode:

```powershell
.\scripts\setup.ps1
```

What this does:

1. creates `.venv`
2. upgrades `pip`
3. installs the package with `pip install -e .[dev]`

Run the automated test suite:

```powershell
.\scripts\test.ps1
```

Run only the opt-in manual integration tests:

```powershell
$env:TON_SBT_RUN_INTEGRATION=1
.\scripts\test.ps1 tests\test_integration_manual.py -q
```

## Quick Start

### 1. Choose the owner wallet strategy

You do not have to create a new owner wallet with this CLI.

You can use either of these approaches:

- use an existing wallet by pasting its mnemonic into `.env`
- create a new wallet with `wallet-new`

Use an existing wallet when:

- you already have a funded wallet
- you want to mint from a wallet you control today
- you want to keep one stable owner or authority address for the collection

Create a new wallet when:

- you are testing the system from scratch
- you want a clean dedicated owner wallet
- you do not already have a funded TON wallet for this workflow

If you already have a wallet, set these values directly in `.env`:

```env
MNEMONIC=your existing 24-word mnemonic
WALLET_VERSION=v5r1
```

If you want to create a new wallet instead, use one of these commands:

If your funded wallet is W5:

```powershell
.\scripts\run.ps1 wallet-new --wallet-version v5r1
```

If you need W4:

```powershell
.\scripts\run.ps1 wallet-new --wallet-version v4r2
```

Shortcut:

```powershell
.\scripts\new-wallet.ps1 --wallet-version v5r1
```

Copy these values from the output into `.env`:

- `MNEMONIC=...`
- `WALLET_VERSION=...`
- the printed testnet address for funding

### 2. Configure `.env`

Minimal first-run configuration:

```env
MNEMONIC=your 24 words here
WALLET_VERSION=v5r1
COLLECTION_ADDRESS=
IS_TESTNET=true

COLLECTION_METADATA_URL=https://example.com/collection.json
ITEMS_BASE_URL=https://example.com/metadata/
ITEM_METADATA_SUFFIX=

TONCENTER_API_KEY=
TONCENTER_ENDPOINT=
TONCENTER_RPS_LIMIT=1
TONCENTER_RPS_PERIOD=1.0

SBT_COLLECTION_CODE_BOC=contracts/nft-collection.boc
SBT_ITEM_CODE_BOC=contracts/nft-item-sbt.boc
```

Rules:

- keep `COLLECTION_ADDRESS=` empty for the first deploy
- use `WALLET_VERSION=v5r1` for funded W5 wallets
- use `WALLET_VERSION=v4r2` for funded W4 wallets
- `ITEMS_BASE_URL` supports both prefix mode and fixed-file mode
- `ITEM_METADATA_SUFFIX` is optional and is used only in prefix mode
- the BOC paths are optional; built-in `tonutils` code is used if files are missing
- `TONCENTER_API_KEY` is optional but recommended for better reliability and fewer rate-limit issues

`ITEMS_BASE_URL` behavior:

- prefix mode: if `ITEMS_BASE_URL=https://example.com/nft/`, the CLI stores item metadata as `ITEMS_BASE_URL + suffix`
- fixed-file mode: if `ITEMS_BASE_URL=https://example.com/nft/176.json`, every minted SBT points to that exact file

Precedence rules:

- if `ITEMS_BASE_URL` is a concrete file URL, it overrides per-index generation and `ITEM_METADATA_SUFFIX`
- if `ITEMS_BASE_URL` is a prefix and `ITEM_METADATA_SUFFIX` is set, every minted SBT uses that same suffix under the prefix
- if `ITEMS_BASE_URL` is a prefix and `ITEM_METADATA_SUFFIX` is empty, the CLI generates `0.json`, `1.json`, `2.json`, and so on

## Network Modes

### Testnet

Use testnet when:

- you are validating the full workflow for the first time
- you are testing metadata and recipient formatting
- you are checking wallet version, balances, deploy logic, or verification logic

Testnet configuration:

```env
IS_TESTNET=true
COLLECTION_ADDRESS=
```

Testnet rules:

- fund the owner wallet with test TON only
- it is safe to use generated wallets for recipients
- it is acceptable to reuse one fixed test metadata suffix such as `176.json`
- always run `doctor` before `run`

Recommended testnet flow:

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1 doctor --wallets wallets.txt
.\scripts\run.ps1 run --wallets wallets.txt
```

### Mainnet

Use mainnet only after the testnet flow is already working.

Mainnet configuration:

```env
IS_TESTNET=false
```

Mainnet rules:

- use a real funded owner wallet
- prefer an existing wallet mnemonic instead of generating a new wallet unless you explicitly want a new dedicated owner
- use a real recipient list supplied by the user, CRM, export, or production process
- verify metadata URLs and suffix rules before sending transactions
- verify the collection settings before the first irreversible deploy

Recommended mainnet flow:

```powershell
.\scripts\run.ps1 doctor --wallets wallets.txt
.\scripts\run.ps1 deploy
.\scripts\run.ps1 mint --wallets wallets.txt
```

Mainnet safety guidance:

- test with a small recipient list first
- confirm `WALLET_VERSION` matches the real owner wallet
- confirm `COLLECTION_ADDRESS` is empty before first deploy and preserved after deploy
- keep a backup of the mnemonic outside the project directory

### 3. Fund the owner wallet

Before `deploy` or `run`, the owner wallet must have enough balance on the selected network.

Balance guidance:

- testnet: fund with test TON
- mainnet: fund with real TON and keep extra balance for deploy, mint value, and network fees

Approximate minimum values used by this project:

- collection deploy: about `0.05 TON`
- mint message per one SBT: about `0.02 TON`
- forwarded amount into the new SBT item: about `0.005 TON`

Practical funding guidance:

- first deploy with one SBT: roughly `0.07 TON` plus fees
- first deploy with ten SBTs: roughly `0.25 TON` plus fees
- keep extra balance above the minimum, especially on mainnet

Network rule:

- testnet TON and mainnet TON are separate
- you must have funds on the owner wallet in the same network where you are running the command
- testnet balance does not help on mainnet, and mainnet balance does not help on testnet

Testnet funding source:

- for this guide, get test TON from `t.me/testgiver_ton_bot`

### 4. Generate recipient wallets

`wallets-generate` is a test helper, not a production recipient sourcing method.

Use it only when:

- you want to test deploy and mint end to end
- you need disposable recipient addresses
- you are validating metadata or verification logic

Do not use generated wallets as your real production recipient source.
For real minting, prepare `wallets.txt` from the actual user wallet list.

Recipient file location rules:

- default location: keep `wallets.txt` in the project root
- alternative: keep the file anywhere and pass the exact path with `--wallets`
- the CLI does not require the file to be in a special folder if you pass `--wallets`

Generate ten test wallets:

```powershell
.\scripts\run.ps1 wallets-generate --count 10
```

Write recipient addresses directly into `wallets.txt`:

```powershell
.\scripts\run.ps1 wallets-generate --count 10 --addresses-out wallets.txt
```

### 5. Validate before sending transactions

```powershell
.\scripts\run.ps1 doctor --wallets wallets.txt
```

### 6. Deploy and mint

```powershell
.\scripts\run.ps1 run --wallets wallets.txt
```

## Commands

### `wallet-new`

Create one wallet:

```powershell
.\scripts\run.ps1 wallet-new --wallet-version v5r1
```

Examples:

```powershell
.\scripts\run.ps1 wallet-new --wallet-version v5r1 --label owner
.\scripts\run.ps1 wallet-new --wallet-version v4r2 --words 24
```

### `wallets-generate`

Generate recipient wallets in batch:

```powershell
.\scripts\run.ps1 wallets-generate --count 10 --wallet-version v5r1
```

Examples:

```powershell
.\scripts\run.ps1 wallets-generate --count 10 --addresses-out wallets.txt
.\scripts\run.ps1 wallets-generate --count 50 --label sbt-test
```

Important:

- this command is for testing and system validation
- the generated mnemonics are stored in `generated_wallets/`
- production minting should use a user-provided recipient file instead of generated test wallets

### `doctor`

Dry-run diagnostics:

```powershell
.\scripts\run.ps1 doctor --wallets wallets.txt
```

Checks:

- `.env`
- wallet version and derived address
- owner wallet balance and state
- collection and item code availability
- recipient file parsing
- projected collection address
- existing `COLLECTION_ADDRESS`, if already set

### `deploy`

Deploy the collection only:

```powershell
.\scripts\run.ps1 deploy
```

### `mint`

Mint into an existing collection:

```powershell
.\scripts\run.ps1 mint --wallets wallets.txt
```

Examples:

```powershell
.\scripts\run.ps1 mint --wallets wallets.txt --batch-size 100
.\scripts\run.ps1 mint --wallets wallets.txt --no-verify
```

Requires `COLLECTION_ADDRESS` in `.env`.

### `run`

Deploy if needed, then mint:

```powershell
.\scripts\run.ps1 run --wallets wallets.txt
```

Examples:

```powershell
.\scripts\run.ps1 run --wallets wallets.txt --batch-size 100
.\scripts\run.ps1 run --wallets generated_wallets\test-wallets-<timestamp>.txt
```

### `test`

Run the automated test suite:

```powershell
.\scripts\test.ps1
```

Examples:

```powershell
.\scripts\test.ps1 -q
.\scripts\test.ps1 tests\test_cli_metadata.py
.\scripts\test.ps1 tests\test_integration_manual.py -q
```

## Test Metadata Example

For smoke testing:

```env
COLLECTION_METADATA_URL=https://save.followdragons.monster/collections/followdragons/collection.json
ITEMS_BASE_URL=https://save.followdragons.monster/collections/followdragons/metadata/
ITEM_METADATA_SUFFIX=176.json
```

This means:

- collection metadata comes from `collection.json`
- every minted SBT points to the metadata suffix `176.json`

This is useful for testnet smoke tests only.
For production, prepare your real metadata structure and use the intended suffix scheme.

Alternative fixed-file smoke test:

```env
COLLECTION_METADATA_URL=https://save.followdragons.monster/collections/followdragons/collection.json
ITEMS_BASE_URL=https://save.followdragons.monster/collections/followdragons/metadata/176.json
ITEM_METADATA_SUFFIX=
```

This means:

- the collection common prefix is stored as empty
- every minted SBT points directly to `176.json`
- `ITEM_METADATA_SUFFIX` is ignored because `ITEMS_BASE_URL` already points to a concrete file

## Data Standards

Use these standards consistently so the CLI behaves predictably and the mint data remains auditable.

### `.env` standards

- file format: plain text UTF-8
- one `KEY=value` pair per line
- no quotes unless the value itself requires them in your own tooling
- keep URLs absolute, including the protocol, for example `https://...`
- keep TON amounts in decimal TON units, not nanotons
- keep booleans as `true` or `false`
- leave `COLLECTION_ADDRESS` empty for the first deploy

Required operational fields:

- `MNEMONIC`
- `WALLET_VERSION`
- `IS_TESTNET`
- `COLLECTION_METADATA_URL`
- `ITEMS_BASE_URL`

Optional operational fields:

- `COLLECTION_ADDRESS`
- `ITEM_METADATA_SUFFIX`
- `TONCENTER_API_KEY`
- `TONCENTER_ENDPOINT`
- `SBT_COLLECTION_CODE_BOC`
- `SBT_ITEM_CODE_BOC`

### Recipient file standards

The recipient file used by `doctor`, `mint`, and `run` must follow these rules:

- default filename and location: `wallets.txt` in the project root
- alternative location: any path passed with `--wallets`
- plain text UTF-8
- one TON address per line
- no commas
- no JSON
- no tabular formatting
- no duplicate addresses unless duplicate minting is intentional
- keep the file generated from the real user source of truth for production

Valid example:

```text
EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c
kQBBYzw3-N7wle1V7KJJv9yQopTB_iNuEX93e8UgUFsIGQGf
```

Recommended production practice:

- prepare the final recipient file separately
- review it before minting
- archive the exact file used for each mint run

### Metadata standards

- `COLLECTION_METADATA_URL` should point to one collection JSON document
- `ITEMS_BASE_URL` may be either a common prefix or one concrete metadata file
- item suffixes should be deterministic and documented when prefix mode is used
- for smoke tests, either `ITEM_METADATA_SUFFIX` may point every token to one known file or `ITEMS_BASE_URL` may point directly to one file
- for production, prefer a suffix strategy that maps clearly to item indices or business identifiers

Examples:

- base URL: `https://example.com/metadata/`
- per-item suffixes: `0.json`, `1.json`, `2.json`
- fixed-file URL: `https://example.com/metadata/176.json`
- smoke-test suffix: `176.json`

Resolution rules:

- prefix mode with empty `ITEM_METADATA_SUFFIX`:
  - item `0` -> `https://example.com/metadata/0.json`
  - item `1` -> `https://example.com/metadata/1.json`
- prefix mode with `ITEM_METADATA_SUFFIX=176.json`:
  - every item -> `https://example.com/metadata/176.json`
- fixed-file mode with `ITEMS_BASE_URL=https://example.com/metadata/176.json`:
  - every item -> `https://example.com/metadata/176.json`

### Contract artifact standards

- keep custom BOCs under `contracts/`
- use stable filenames when possible
- treat custom BOCs as versioned deployment artifacts
- if you do not supply BOCs, the CLI falls back to the built-in `tonutils` code

## Operational Standards

Use this operating model for clean, repeatable runs:

1. Prepare or verify the owner wallet mnemonic and `WALLET_VERSION`.
2. Prepare metadata URLs.
3. Prepare the recipient file.
4. Run `doctor`.
5. On first deploy, keep `COLLECTION_ADDRESS` empty.
6. Run `deploy` or `run`.
7. Archive the final recipient file and resulting collection address.

Production recommendation:

- use `wallets-generate` only for testnet system checks
- use real user recipient data for real minting
- separate test artifacts from production recipient files

## Test Coverage

The project includes an automated `pytest` suite for the non-network-critical logic:

- `.env` parsing and validation
- TON endpoint normalization
- metadata mode resolution for `ITEMS_BASE_URL`
- recipient file parsing and duplicate filtering
- `.env` collection address persistence

The project also includes a very small optional integration layer:

- file: `tests/test_integration_manual.py`
- marked as `integration` and `manual`
- skipped by default
- runs only when `TON_SBT_RUN_INTEGRATION=1`
- intended for live testnet credentials already present in `.env`
- does not send deploy or mint transactions
- verifies live connectivity, wallet derivation, and collection projection/queryability

What these tests do not cover:

- live deploys against testnet or mainnet
- Toncenter availability
- external wallet balances
- explorer-side verification

Recommended practice:

1. run `.\scripts\test.ps1`
2. optionally run `TON_SBT_RUN_INTEGRATION=1` with `tests\test_integration_manual.py`
3. run `.\scripts\run.ps1 doctor --wallets wallets.txt`
4. run live testnet transactions
5. only then move to mainnet

## Important Notes

### `WALLET_VERSION`

The same mnemonic resolves to different addresses for `v4r2` and `v5r1`.

If you use the wrong version:

- the CLI derives a different address
- the balance may appear as `0 TON`
- the wallet may appear as `nonexist`

### `COLLECTION_ADDRESS`

- first run: keep it empty
- after `deploy` or `run`: the CLI writes it automatically
- later `mint` runs: reuse the saved address

### Toncenter rate limits

The public testnet endpoint can return `429 Ratelimit exceed`.

Built into this project:

- `DEFAULT_HTTP_RETRY_POLICY` from `tonutils`
- conservative default limit:

```env
TONCENTER_RPS_LIMIT=1
TONCENTER_RPS_PERIOD=1.0
```

Safer but slower mode:

```env
TONCENTER_RPS_LIMIT=1
TONCENTER_RPS_PERIOD=2.0
```

Recommendation:

- if you have a Toncenter API key, set `TONCENTER_API_KEY` in `.env`
- this improves reliability on both testnet and mainnet
- it reduces the chance of public rate-limit failures during `doctor`, `deploy`, `mint`, and `run`

How to get a key:

- official TON Docs guide: https://docs.ton.org/ecosystem/api/toncenter/get-api-key
- Toncenter bot: https://t.me/toncenter

### Contract BOCs

`contracts/` may contain:

- `nft-collection.boc`
- `nft-item-sbt.boc`

These files are optional.
If they are missing, the CLI uses built-in compiled contract code from `tonutils`.

## Output Guidance

After successful completion, the CLI prints a `Next` block explaining the most likely next action:

- after `wallet-new`
- after `wallets-generate`
- after `doctor`
- after `deploy`
- after `mint`
- after `run`

## Security

- `generated_wallets/` contains mnemonic phrases and private key material
- the directory is ignored by git
- do not publish these files into a public repository
- do not treat generated test wallets as production user wallets

## License

This project is licensed under the MIT License.
See [LICENSE](d:/TON/SBT%20Minting/LICENSE).

## References

- TON NFT reference: https://docs.ton.org/standard/tokens/nft/reference
- TON NFT deploy guide: https://docs.ton.org/standard/tokens/nft/deploy
- TON SBT guide: https://docs.ton.org/standard/tokens/nft/sbt
- TON Docs, Toncenter API key: https://docs.ton.org/ecosystem/api/toncenter/get-api-key
- Token contracts repo: https://github.com/ton-blockchain/token-contract
- tonutils docs: https://tonutils.com
