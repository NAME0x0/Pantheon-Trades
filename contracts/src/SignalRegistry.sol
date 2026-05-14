// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title SignalRegistry
/// @notice Lightweight on-chain index of every Apollo signal that reached
///         Boule. Stores only (signal hash, market id, band, recorded_at).
///         The full Signal lives off-chain in Parthenon's IPFS bundle.
contract SignalRegistry is AccessControl {
    bytes32 public constant SIGNAL_ROLE = keccak256("SIGNAL_ROLE");

    struct SignalRecord {
        bytes32 signalHash;
        string  marketId;
        string  band;
        address recordedBy;
        uint64  recordedAt;
    }

    mapping(bytes32 => SignalRecord) private _records;

    event SignalRecorded(
        bytes32 indexed signalId,
        bytes32 signalHash,
        string  marketId,
        string  band,
        address indexed recordedBy,
        uint64  recordedAt
    );

    error AlreadyRecorded(bytes32 signalId);
    error EmptyHash();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SIGNAL_ROLE, admin);
    }

    function record(
        bytes32 signalId,
        bytes32 signalHash,
        string calldata marketId,
        string calldata band
    ) external onlyRole(SIGNAL_ROLE) {
        if (signalHash == bytes32(0)) revert EmptyHash();
        if (_records[signalId].signalHash != bytes32(0)) revert AlreadyRecorded(signalId);

        _records[signalId] = SignalRecord({
            signalHash: signalHash,
            marketId: marketId,
            band: band,
            recordedBy: msg.sender,
            recordedAt: uint64(block.timestamp)
        });
        emit SignalRecorded(signalId, signalHash, marketId, band, msg.sender, uint64(block.timestamp));
    }

    function recordOf(bytes32 signalId) external view returns (SignalRecord memory) {
        return _records[signalId];
    }
}
