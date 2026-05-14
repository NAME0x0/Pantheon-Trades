// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IElysium {
    event BacktestPublished(bytes32 indexed runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6);

    function publish(bytes32 runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6) external;
    function get(bytes32 runId)
        external
        view
        returns (int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6, uint64 publishedAt);
}
