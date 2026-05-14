// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Elysium
/// @notice On-chain registry of published backtest runs.
contract Elysium is AccessControl {
    bytes32 public constant PUBLISHER_ROLE = keccak256("PUBLISHER_ROLE");

    struct Run {
        int256  realisedPnlUsdc6;
        uint256 nTrades;
        uint256 sharpeE6;
        uint64  publishedAt;
    }

    mapping(bytes32 => Run) private _runs;

    event BacktestPublished(bytes32 indexed runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PUBLISHER_ROLE, admin);
    }

    function publish(bytes32 runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6)
        external
        onlyRole(PUBLISHER_ROLE)
    {
        _runs[runId] = Run({
            realisedPnlUsdc6: realisedPnlUsdc6,
            nTrades: nTrades,
            sharpeE6: sharpeE6,
            publishedAt: uint64(block.timestamp)
        });
        emit BacktestPublished(runId, realisedPnlUsdc6, nTrades, sharpeE6);
    }

    function get(bytes32 runId)
        external
        view
        returns (int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6, uint64 publishedAt)
    {
        Run storage r = _runs[runId];
        return (r.realisedPnlUsdc6, r.nTrades, r.sharpeE6, r.publishedAt);
    }
}
