// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentPassport {
    event PassportMinted(string indexed agentId, uint256 version, string metadataCid, address indexed issuer);
    event PassportRevoked(string indexed agentId, address indexed issuer);

    function mint(string calldata agentId, uint256 version, string calldata metadataCid, string[] calldata skills) external;
    function revoke(string calldata agentId) external;
    function get(string calldata agentId)
        external
        view
        returns (uint256 version, string memory metadataCid, string[] memory skills, address issuer, bool active);
}
