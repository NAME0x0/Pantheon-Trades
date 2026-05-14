// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title GoalsBoard
/// @notice Live Olympus goal progress mirrored on-chain.
contract GoalsBoard is AccessControl {
    bytes32 public constant GOAL_ROLE = keccak256("GOAL_ROLE");

    struct Goal {
        string  title;
        int256  targetE6;
        int256  currentE6;
        uint32  horizonDays;
        uint8   status;     // 0=open, 1=on_track, 2=at_risk, 3=achieved, 4=missed
        uint64  updatedAt;
    }

    mapping(bytes32 => Goal) private _goals;

    event GoalSet(bytes32 indexed goalId, string title, int256 targetE6, uint32 horizonDays);
    event GoalProgress(bytes32 indexed goalId, int256 currentE6, uint8 status);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOAL_ROLE, admin);
    }

    function setGoal(bytes32 goalId, string calldata title, int256 targetE6, uint32 horizonDays)
        external
        onlyRole(GOAL_ROLE)
    {
        Goal storage g = _goals[goalId];
        g.title = title;
        g.targetE6 = targetE6;
        g.horizonDays = horizonDays;
        g.updatedAt = uint64(block.timestamp);
        emit GoalSet(goalId, title, targetE6, horizonDays);
    }

    function updateProgress(bytes32 goalId, int256 currentE6, uint8 status) external onlyRole(GOAL_ROLE) {
        Goal storage g = _goals[goalId];
        g.currentE6 = currentE6;
        g.status = status;
        g.updatedAt = uint64(block.timestamp);
        emit GoalProgress(goalId, currentE6, status);
    }

    function get(bytes32 goalId)
        external
        view
        returns (
            string memory title,
            int256 targetE6,
            int256 currentE6,
            uint32 horizonDays,
            uint8 status,
            uint64 updatedAt
        )
    {
        Goal storage g = _goals[goalId];
        return (g.title, g.targetE6, g.currentE6, g.horizonDays, g.status, g.updatedAt);
    }
}
