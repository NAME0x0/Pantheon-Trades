// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC8004 {
    function isAgent(string calldata agentId) external view returns (bool);
    function metadataOf(string calldata agentId) external view returns (string memory);
}
