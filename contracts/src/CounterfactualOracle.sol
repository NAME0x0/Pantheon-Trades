// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title CounterfactualOracle
/// @notice Persistent record of Elysium counterfactual studies.
contract CounterfactualOracle is AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");

    struct Entry {
        string  label;
        int256  deltaPnlUsdc6;
        address author;
        uint64  recordedAt;
    }

    mapping(bytes32 => Entry) private _entries;

    event CounterfactualRecorded(bytes32 indexed key, string label, int256 deltaPnlUsdc6, address indexed author);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ORACLE_ROLE, admin);
    }

    function record(bytes32 key, string calldata label, int256 deltaPnlUsdc6) external onlyRole(ORACLE_ROLE) {
        _entries[key] = Entry({
            label: label,
            deltaPnlUsdc6: deltaPnlUsdc6,
            author: msg.sender,
            recordedAt: uint64(block.timestamp)
        });
        emit CounterfactualRecorded(key, label, deltaPnlUsdc6, msg.sender);
    }

    function get(bytes32 key)
        external
        view
        returns (string memory label, int256 deltaPnlUsdc6, address author, uint64 recordedAt)
    {
        Entry storage e = _entries[key];
        return (e.label, e.deltaPnlUsdc6, e.author, e.recordedAt);
    }
}
