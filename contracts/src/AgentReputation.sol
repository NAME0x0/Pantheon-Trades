// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReputationRegistry} from "./erc8004/ReputationRegistry.sol";

/// @title AgentReputation
/// @notice Pantheon wrapper around the ERC-8004 ReputationRegistry.
contract AgentReputation is ReputationRegistry {
    constructor(address admin) ReputationRegistry(admin) {}
}
