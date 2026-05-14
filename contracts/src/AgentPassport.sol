// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IdentityRegistry} from "./erc8004/IdentityRegistry.sol";

/// @title AgentPassport
/// @notice Thin Pantheon-flavoured wrapper around the ERC-8004 IdentityRegistry.
///         All storage lives in IdentityRegistry; this contract just exposes
///         the Pantheon-specific deploy + admin events.
contract AgentPassport is IdentityRegistry {
    constructor(address admin) IdentityRegistry(admin) {}
}
