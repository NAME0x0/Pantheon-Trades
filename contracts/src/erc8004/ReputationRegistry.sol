// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ReputationRegistry
/// @notice Stores per-agent reputation snapshots (Brier in bps + credibility
///         weight in bps + total prediction count) so any consumer of the
///         ERC-8004 identity can look up live agent quality.
contract ReputationRegistry is AccessControl {
    bytes32 public constant REPUTATION_ROLE = keccak256("REPUTATION_ROLE");

    struct ReputationEntry {
        uint256 brierBps;
        uint256 credibilityBps;
        uint256 predictionCount;
        uint64  updatedAt;
    }

    mapping(string => ReputationEntry) private _entries;

    event Updated(
        string indexed agentId,
        uint256 brierBps,
        uint256 credibilityBps,
        uint256 predictionCount,
        uint64  updatedAt
    );

    error EmptyAgentId();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REPUTATION_ROLE, admin);
    }

    function update(
        string calldata agentId,
        uint256 brierBps,
        uint256 credibilityBps,
        uint256 predictionCount
    ) external onlyRole(REPUTATION_ROLE) {
        if (bytes(agentId).length == 0) revert EmptyAgentId();
        _entries[agentId] = ReputationEntry({
            brierBps: brierBps,
            credibilityBps: credibilityBps,
            predictionCount: predictionCount,
            updatedAt: uint64(block.timestamp)
        });
        emit Updated(agentId, brierBps, credibilityBps, predictionCount, uint64(block.timestamp));
    }

    function get(string calldata agentId)
        external
        view
        returns (uint256 brierBps, uint256 credibilityBps, uint256 predictionCount, uint64 updatedAt)
    {
        ReputationEntry storage rec = _entries[agentId];
        return (rec.brierBps, rec.credibilityBps, rec.predictionCount, rec.updatedAt);
    }
}
