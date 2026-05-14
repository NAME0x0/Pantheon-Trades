// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title EmergencyPause
/// @notice Operator-controlled kill switch. Reads ``paused()`` to decide
///         whether a wired contract should refuse mutating calls.
contract EmergencyPause is AccessControl {
    bytes32 public constant PAUSE_ROLE = keccak256("PAUSE_ROLE");

    bool private _paused;
    string public reason;

    event Paused(address indexed by, string reason);
    event Unpaused(address indexed by);

    error NotPaused();
    error AlreadyPaused();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PAUSE_ROLE, admin);
    }

    function pause(string calldata _reason) external onlyRole(PAUSE_ROLE) {
        if (_paused) revert AlreadyPaused();
        _paused = true;
        reason = _reason;
        emit Paused(msg.sender, _reason);
    }

    function unpause() external onlyRole(PAUSE_ROLE) {
        if (!_paused) revert NotPaused();
        _paused = false;
        delete reason;
        emit Unpaused(msg.sender);
    }

    function paused() external view returns (bool) {
        return _paused;
    }
}
