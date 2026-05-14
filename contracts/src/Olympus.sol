// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Olympus
/// @notice System-state machine mirroring services/olympus/src/olympus/state.py.
contract Olympus is AccessControl {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    uint8 public constant STANDBY  = 0;
    uint8 public constant ACTIVE   = 1;
    uint8 public constant DEGRADED = 2;
    uint8 public constant PAUSED   = 3;
    uint8 public constant RECOVERY = 4;

    uint8 public state = STANDBY;

    event StateChanged(uint8 from_, uint8 to_, string reason, uint64 at);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(OPERATOR_ROLE, admin);
    }

    function transition(uint8 target, string calldata reason) external onlyRole(OPERATOR_ROLE) {
        require(_canMove(state, target), "invalid transition");
        uint8 from_ = state;
        state = target;
        emit StateChanged(from_, target, reason, uint64(block.timestamp));
    }

    function acceptsNewTrades() external view returns (bool) {
        return state == ACTIVE;
    }

    function _canMove(uint8 current, uint8 target) internal pure returns (bool) {
        if (current == STANDBY)  return target == ACTIVE;
        if (current == ACTIVE)   return target == DEGRADED || target == PAUSED;
        if (current == DEGRADED) return target == ACTIVE   || target == PAUSED;
        if (current == PAUSED)   return target == RECOVERY || target == STANDBY;
        if (current == RECOVERY) return target == ACTIVE   || target == STANDBY;
        return false;
    }
}
