// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IThesisRegistry
/// @notice Surface used by `parthenon.anchor.AnchorService` (off-chain) to
///         commit archived thesis bundles on-chain. The on-chain contract
///         stores a (kind, manifestCid, merkleRoot) tuple and emits an
///         indexable event; the full archive lives on IPFS/Irys.
interface IThesisRegistry {
    event Anchored(
        bytes32 indexed manifestId,
        string kind,
        string manifestCid,
        bytes32 indexed merkleRoot,
        address indexed anchoredBy,
        uint64 anchoredAt
    );

    /// @notice Anchor a single archive bundle.
    /// @param kind       Bundle kind ("thesis", "outcome", ...).
    /// @param manifestCid IPFS CID of the manifest tying CIDs + hashes.
    /// @param merkleRoot Root of the OpenZeppelin-style sorted-pair tree
    ///                   computed off-chain over the archive's content hashes.
    function anchor(string calldata kind, string calldata manifestCid, bytes32 merkleRoot)
        external;

    /// @notice Read back the merkle root previously anchored for a manifest CID.
    function rootOf(string calldata manifestCid) external view returns (bytes32);

    /// @notice Verify a leaf belongs to the tree anchored for a manifest CID.
    function verifyProof(
        string calldata manifestCid,
        bytes32 leaf,
        bytes32[] calldata proof
    ) external view returns (bool);
}
