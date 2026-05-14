// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentReputation {
    event ReputationUpdated(string indexed agentId, uint256 brierBps, uint256 credibilityBps, uint256 predictionCount);

    function update(string calldata agentId, uint256 brierBps, uint256 credibilityBps, uint256 predictionCount) external;
    function get(string calldata agentId)
        external
        view
        returns (uint256 brierBps, uint256 credibilityBps, uint256 predictionCount, uint64 updatedAt);
}
