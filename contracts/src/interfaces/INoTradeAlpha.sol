// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface INoTradeAlpha {
    event AvoidedTrade(bytes32 indexed signalHash, string reasonCode, uint256 avoidedNotional, address indexed author, uint64 recordedAt);
    function recordAvoided(bytes32 signalHash, string calldata reasonCode, uint256 avoidedNotional) external;
}
