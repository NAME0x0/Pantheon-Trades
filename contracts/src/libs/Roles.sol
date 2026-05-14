// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Roles
/// @notice Canonical role identifiers used across Pantheon contracts.
library Roles {
    bytes32 internal constant DEFAULT_ADMIN_ROLE = bytes32(0);
    bytes32 internal constant ANCHOR_ROLE         = keccak256("ANCHOR_ROLE");
    bytes32 internal constant SIGNAL_ROLE         = keccak256("SIGNAL_ROLE");
    bytes32 internal constant RESTRAINT_ROLE      = keccak256("RESTRAINT_ROLE");
    bytes32 internal constant ALPHA_ROLE          = keccak256("ALPHA_ROLE");
    bytes32 internal constant EXECUTOR_ROLE       = keccak256("EXECUTOR_ROLE");
    bytes32 internal constant STRATEGOS_ROLE      = keccak256("STRATEGOS_ROLE");
    bytes32 internal constant LIFECYCLE_ROLE      = keccak256("LIFECYCLE_ROLE");
    bytes32 internal constant PAUSE_ROLE          = keccak256("PAUSE_ROLE");
    bytes32 internal constant SCORER_ROLE         = keccak256("SCORER_ROLE");
    bytes32 internal constant PASSPORT_ROLE       = keccak256("PASSPORT_ROLE");
    bytes32 internal constant REPUTATION_ROLE     = keccak256("REPUTATION_ROLE");
    bytes32 internal constant VAULT_ROLE          = keccak256("VAULT_ROLE");
    bytes32 internal constant ORACLE_ROLE         = keccak256("ORACLE_ROLE");
}
