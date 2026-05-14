// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title StrategyLifecycle
/// @notice On-chain mirror of Moirai's strategy state machine.
contract StrategyLifecycle is AccessControl {
    bytes32 public constant LIFECYCLE_ROLE = keccak256("LIFECYCLE_ROLE");

    uint8 public constant DRAFT       = 0;
    uint8 public constant REGISTERED  = 1;
    uint8 public constant PAPER       = 2;
    uint8 public constant LIVE        = 3;
    uint8 public constant SUSPENDED   = 4;
    uint8 public constant TERMINATED  = 5;

    struct Strategy {
        string  name;
        uint8   state;
        uint64  updatedAt;
    }

    mapping(bytes32 => Strategy) private _strategies;

    event Registered(bytes32 indexed strategyId, string name);
    event StateChanged(bytes32 indexed strategyId, uint8 from_, uint8 to_);
    event Terminated(bytes32 indexed strategyId, string reason);

    error InvalidTransition();
    error AlreadyExists();
    error Unknown();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(LIFECYCLE_ROLE, admin);
    }

    function register(bytes32 strategyId, string calldata name) external onlyRole(LIFECYCLE_ROLE) {
        if (bytes(_strategies[strategyId].name).length != 0) revert AlreadyExists();
        _strategies[strategyId] = Strategy({name: name, state: DRAFT, updatedAt: uint64(block.timestamp)});
        emit Registered(strategyId, name);
    }

    function transition(bytes32 strategyId, uint8 target) external onlyRole(LIFECYCLE_ROLE) {
        Strategy storage s = _strategies[strategyId];
        if (bytes(s.name).length == 0) revert Unknown();
        if (!_isValid(s.state, target)) revert InvalidTransition();
        uint8 from_ = s.state;
        s.state = target;
        s.updatedAt = uint64(block.timestamp);
        emit StateChanged(strategyId, from_, target);
    }

    function terminate(bytes32 strategyId, string calldata reason) external onlyRole(LIFECYCLE_ROLE) {
        Strategy storage s = _strategies[strategyId];
        if (bytes(s.name).length == 0) revert Unknown();
        s.state = TERMINATED;
        s.updatedAt = uint64(block.timestamp);
        emit Terminated(strategyId, reason);
    }

    function state(bytes32 strategyId) external view returns (uint8) {
        return _strategies[strategyId].state;
    }

    function _isValid(uint8 current, uint8 target) internal pure returns (bool) {
        if (target == TERMINATED) return true; // terminate from anywhere
        if (current == DRAFT)      return target == REGISTERED;
        if (current == REGISTERED) return target == PAPER;
        if (current == PAPER)      return target == LIVE || target == SUSPENDED;
        if (current == LIVE)       return target == SUSPENDED;
        if (current == SUSPENDED)  return target == LIVE;
        return false;
    }
}
