// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {MerkleProof} from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

import {IThesisRegistry} from "./interfaces/IThesisRegistry.sol";

/// @title ThesisRegistry
/// @notice Anchors Parthenon archive bundles on-chain. Each call stores a
///         merkle root + manifest CID under the keccak hash of the CID.
///         Re-anchoring the same CID is rejected — manifests are immutable
///         once published. Only addresses with ANCHOR_ROLE can write.
///
/// @dev    The on-chain payload is intentionally tiny: only the root, the
///         CID, and the kind tag. The full archive (signal, thesis, trace,
///         outcome) lives on IPFS/Irys; the root proves any leaf.
contract ThesisRegistry is AccessControl, IThesisRegistry {
    bytes32 public constant ANCHOR_ROLE = keccak256("ANCHOR_ROLE");

    struct AnchorRecord {
        bytes32 merkleRoot;
        string kind;
        string manifestCid;
        address anchoredBy;
        uint64 anchoredAt;
    }

    /// @dev keccak256(bytes(manifestCid)) => record.
    mapping(bytes32 => AnchorRecord) private _records;

    error AlreadyAnchored(string manifestCid);
    error EmptyCid();
    error ZeroRoot();
    error UnknownManifest(string manifestCid);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ANCHOR_ROLE, admin);
    }

    /// @inheritdoc IThesisRegistry
    function anchor(
        string calldata kind,
        string calldata manifestCid,
        bytes32 merkleRoot
    ) external onlyRole(ANCHOR_ROLE) {
        if (bytes(manifestCid).length == 0) revert EmptyCid();
        if (merkleRoot == bytes32(0)) revert ZeroRoot();

        bytes32 manifestId = keccak256(bytes(manifestCid));
        if (_records[manifestId].merkleRoot != bytes32(0)) {
            revert AlreadyAnchored(manifestCid);
        }

        _records[manifestId] = AnchorRecord({
            merkleRoot: merkleRoot,
            kind: kind,
            manifestCid: manifestCid,
            anchoredBy: msg.sender,
            anchoredAt: uint64(block.timestamp)
        });

        emit Anchored(
            manifestId, kind, manifestCid, merkleRoot, msg.sender, uint64(block.timestamp)
        );
    }

    /// @inheritdoc IThesisRegistry
    function rootOf(string calldata manifestCid) external view returns (bytes32) {
        return _records[keccak256(bytes(manifestCid))].merkleRoot;
    }

    /// @notice Full anchor record for a manifest CID.
    function recordOf(string calldata manifestCid) external view returns (AnchorRecord memory) {
        bytes32 manifestId = keccak256(bytes(manifestCid));
        AnchorRecord memory rec = _records[manifestId];
        if (rec.merkleRoot == bytes32(0)) revert UnknownManifest(manifestCid);
        return rec;
    }

    /// @inheritdoc IThesisRegistry
    function verifyProof(
        string calldata manifestCid,
        bytes32 leaf,
        bytes32[] calldata proof
    ) external view returns (bool) {
        bytes32 root = _records[keccak256(bytes(manifestCid))].merkleRoot;
        if (root == bytes32(0)) return false;
        return MerkleProof.verify(proof, root, leaf);
    }

    /// @notice Stable identifier hashing scheme matching
    ///         `parthenon.hash.thesis_hash` off-chain.
    function thesisHash(
        string calldata thesisId,
        string calldata marketId,
        uint256 councilProbabilityE6,
        string calldata direction
    ) external pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                thesisId, "|", marketId, "|", _formatE6(councilProbabilityE6), "|", direction
            )
        );
    }

    /// @dev Render a fixed-point value with 6 fractional digits, matching
    ///      Python's `f"{value:.6f}"` so off-chain and on-chain hashes agree.
    function _formatE6(uint256 e6) private pure returns (string memory) {
        uint256 integerPart = e6 / 1_000_000;
        uint256 fractionalPart = e6 % 1_000_000;
        return string.concat(_toString(integerPart), ".", _padFractional(fractionalPart));
    }

    function _padFractional(uint256 value) private pure returns (string memory) {
        bytes memory out = new bytes(6);
        for (uint256 i = 6; i > 0; --i) {
            out[i - 1] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return string(out);
    }

    function _toString(uint256 value) private pure returns (string memory) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            ++digits;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            --digits;
            buffer[digits] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}
