// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IOstrakon {
    event WeightUpdated(string indexed agentId, uint256 credibilityBps);

    function setWeight(string calldata agentId, uint256 credibilityBps) external;
    function weight(string calldata agentId) external view returns (uint256);
}
