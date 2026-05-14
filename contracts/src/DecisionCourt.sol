// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title DecisionCourt
/// @notice On-chain ledger of Areopagus thesis decisions.
contract DecisionCourt is AccessControl {
    bytes32 public constant COURT_ROLE = keccak256("COURT_ROLE");

    uint8 public constant DECISION_APPROVED = 1;
    uint8 public constant DECISION_REJECTED = 2;
    uint8 public constant DECISION_RESIZED  = 3;

    struct Decision {
        uint8   decision;
        string  reasonCode;
        string  note;
        uint64  recordedAt;
    }

    mapping(bytes32 => Decision) private _decisions;

    event DecisionRecorded(bytes32 indexed thesisId, uint8 decision, string reasonCode, string note, address indexed by);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(COURT_ROLE, admin);
    }

    function record(bytes32 thesisId, uint8 decision, string calldata reasonCode, string calldata note)
        external
        onlyRole(COURT_ROLE)
    {
        _decisions[thesisId] = Decision(decision, reasonCode, note, uint64(block.timestamp));
        emit DecisionRecorded(thesisId, decision, reasonCode, note, msg.sender);
    }

    function get(bytes32 thesisId)
        external
        view
        returns (uint8 decision, string memory reasonCode, string memory note, uint64 recordedAt)
    {
        Decision storage d = _decisions[thesisId];
        return (d.decision, d.reasonCode, d.note, d.recordedAt);
    }
}
