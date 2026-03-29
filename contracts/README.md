Place compiled contract BOCs here if you want to use your own pinned contract artifacts.

This directory is optional.
If these files are missing, the CLI falls back to the built-in compiled contract code provided by `tonutils`.

- `nft-collection.boc` from the reference `nft-collection.fc`
- `nft-item-sbt.boc` from `nft-item-sbt.fc` (SBT item, not regular NFT item)

Expected paths are configured in `.env`:

- `SBT_COLLECTION_CODE_BOC=contracts/nft-collection.boc`
- `SBT_ITEM_CODE_BOC=contracts/nft-item-sbt.boc`
