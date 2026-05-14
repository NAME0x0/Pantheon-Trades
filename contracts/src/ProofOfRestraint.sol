// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ProofOfRestraint
/// @notice On-chain witness that Pantheon observed a signal and declined
///         to trade. Each entry binds (signalHash, marketId, reasonCode)
///         so anyone can verify the discipline was actually paid.
///
/// @dev    Records are append-only. The contract assigns a monotonically
///         increasing proofId per call so off-chain consumers can paginate.
contract ProofOfRestraint is AccessControl {
    bytes32 public constant RESTRAINT_ROLE = keccak256("RESTRAINT_ROLE");

    struct RestraintRecord {
        uint256 proofId;
        bytes32 signalHash;
        string  marketId;
        string  reasonCode;
        string  note;
        address author;
        uint64  recordedAt;
    }

    uint256 public nextProofId;
    mapping(uint256 => RestraintRecord) private _records;

    event Restrained(
        uint256 indexed proofId,
        bytes32 indexed signalHash,
        string  marketId,
        string  reasonCode,
        string  note,
        address indexed author,
        uint64  recordedAt
    );

    error EmptyHash();
    error EmptyReason();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RESTRAINT_ROLE, admin);
    }

    function declineTrade(
        bytes32 signalHash,
        string calldata marketId,
        string calldata reasonCode,
        string calldata note
    ) external onlyRole(RESTRAINT_ROLE) returns (uint256 proofId) {
        if (signalHash == bytes32(0)) revert EmptyHash();
        if (bytes(reasonCode).length == 0) revert EmptyReason();

        proofId = ++nextProofId;
        _records[proofId] = RestraintRecord({
            proofId: proofId,
            signalHash: signalHash,
            marketId: marketId,
            reasonCode: reasonCode,
            note: note,
            author: msg.sender,
            recordedAt: uint64(block.timestamp)
        });
        emit Restrained(
            proofId, signalHash, marketId, reasonCode, note, msg.sender, uint64(block.timestamp)
        );
    }

    function recordOf(uint256 proofId) external view returns (RestraintRecord memory) {
        return _records[proofId];
    }
}
