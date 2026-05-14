// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {ThesisRegistry} from "./ThesisRegistry.sol";

/// @title Parthenon
/// @notice High-level facade — the Pantheon dashboard imports this and reads
///         the underlying registry plus a top-level "archive index" pointer.
contract Parthenon is AccessControl {
    bytes32 public constant CURATOR_ROLE = keccak256("CURATOR_ROLE");

    ThesisRegistry public immutable registry;
    string public latestIndexCid;

    event IndexUpdated(string indexed indexCid, address indexed by);

    constructor(ThesisRegistry _registry, address admin) {
        registry = _registry;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CURATOR_ROLE, admin);
    }

    function setIndex(string calldata indexCid) external onlyRole(CURATOR_ROLE) {
        latestIndexCid = indexCid;
        emit IndexUpdated(indexCid, msg.sender);
    }
}
