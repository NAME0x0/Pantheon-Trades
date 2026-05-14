// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title RoleManager
/// @notice Centralised role administrator. Other Pantheon contracts can read
///         from this to decide whether a caller is authorised.
contract RoleManager is AccessControl {
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }
}
