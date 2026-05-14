// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IGoalsBoard {
    event GoalSet(bytes32 indexed goalId, string title, int256 targetE6, uint32 horizonDays);
    event GoalProgress(bytes32 indexed goalId, int256 currentE6, uint8 status);

    function setGoal(bytes32 goalId, string calldata title, int256 targetE6, uint32 horizonDays) external;
    function updateProgress(bytes32 goalId, int256 currentE6, uint8 status) external;
}
