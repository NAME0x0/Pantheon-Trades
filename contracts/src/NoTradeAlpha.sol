// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title NoTradeAlpha
/// @notice Tracks notional avoided loss whenever Areopagus declines a trade.
///         Operates as a counter on (reasonCode, totalAvoidedNotional) so
///         the dashboard can answer "how much did discipline save us?".
contract NoTradeAlpha is AccessControl {
    bytes32 public constant ALPHA_ROLE = keccak256("ALPHA_ROLE");

    mapping(string => uint256) public reasonCounts;
    mapping(string => uint256) public reasonNotional;
    uint256 public totalAvoidedNotional;
    uint256 public totalDeclines;

    event AvoidedTrade(
        bytes32 indexed signalHash,
        string  reasonCode,
        uint256 avoidedNotional,
        address indexed author,
        uint64  recordedAt
    );

    error EmptyReason();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ALPHA_ROLE, admin);
    }

    function recordAvoided(
        bytes32 signalHash,
        string calldata reasonCode,
        uint256 avoidedNotional
    ) external onlyRole(ALPHA_ROLE) {
        if (bytes(reasonCode).length == 0) revert EmptyReason();
        reasonCounts[reasonCode] += 1;
        reasonNotional[reasonCode] += avoidedNotional;
        totalAvoidedNotional += avoidedNotional;
        totalDeclines += 1;
        emit AvoidedTrade(
            signalHash, reasonCode, avoidedNotional, msg.sender, uint64(block.timestamp)
        );
    }
}
