// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Ostrakon
/// @notice On-chain mirror of agent credibility weights.
contract Ostrakon is AccessControl {
    bytes32 public constant SCORER_ROLE = keccak256("SCORER_ROLE");

    mapping(string => uint256) public weights;   // basis points: 10000 = 1.0
    mapping(string => uint64)  public updatedAt;

    event WeightUpdated(string indexed agentId, uint256 credibilityBps);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCORER_ROLE, admin);
    }

    function setWeight(string calldata agentId, uint256 credibilityBps) external onlyRole(SCORER_ROLE) {
        weights[agentId] = credibilityBps;
        updatedAt[agentId] = uint64(block.timestamp);
        emit WeightUpdated(agentId, credibilityBps);
    }

    function weight(string calldata agentId) external view returns (uint256) {
        return weights[agentId];
    }
}
