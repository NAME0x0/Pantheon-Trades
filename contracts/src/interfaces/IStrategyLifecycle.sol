// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IStrategyLifecycle {
    event StrategyRegistered(bytes32 indexed strategyId, string name);
    event StateChanged(bytes32 indexed strategyId, uint8 from_, uint8 to_);
    event StrategyTerminated(bytes32 indexed strategyId, string reason);

    function register(bytes32 strategyId, string calldata name) external;
    function transition(bytes32 strategyId, uint8 target) external;
    function terminate(bytes32 strategyId, string calldata reason) external;
    function state(bytes32 strategyId) external view returns (uint8);
}
