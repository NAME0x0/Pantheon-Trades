// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC8004} from "./IERC8004.sol";

/// @title IdentityRegistry
/// @notice ERC-8004 agent identity store. Keyed by agent_id; each entry binds
///         a (version, metadataCid, skills, issuer) tuple plus an active bit.
contract IdentityRegistry is AccessControl, IERC8004 {
    bytes32 public constant PASSPORT_ROLE = keccak256("PASSPORT_ROLE");

    struct Identity {
        uint256 version;
        string  metadataCid;
        string[] skills;
        address issuer;
        bool    active;
        uint64  updatedAt;
    }

    mapping(string => Identity) private _agents;

    event Minted(string indexed agentId, uint256 version, string metadataCid, address indexed issuer);
    event Revoked(string indexed agentId, address indexed issuer);

    error EmptyAgentId();
    error VersionMustIncrease();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PASSPORT_ROLE, admin);
    }

    function mint(
        string calldata agentId,
        uint256 version,
        string calldata metadataCid,
        string[] calldata skills
    ) external onlyRole(PASSPORT_ROLE) {
        if (bytes(agentId).length == 0) revert EmptyAgentId();
        Identity storage rec = _agents[agentId];
        if (version <= rec.version) revert VersionMustIncrease();
        rec.version = version;
        rec.metadataCid = metadataCid;
        delete rec.skills;
        for (uint256 i = 0; i < skills.length; ++i) {
            rec.skills.push(skills[i]);
        }
        rec.issuer = msg.sender;
        rec.active = true;
        rec.updatedAt = uint64(block.timestamp);
        emit Minted(agentId, version, metadataCid, msg.sender);
    }

    function revoke(string calldata agentId) external onlyRole(PASSPORT_ROLE) {
        Identity storage rec = _agents[agentId];
        rec.active = false;
        rec.updatedAt = uint64(block.timestamp);
        emit Revoked(agentId, msg.sender);
    }

    function get(string calldata agentId)
        external
        view
        returns (
            uint256 version,
            string memory metadataCid,
            string[] memory skills,
            address issuer,
            bool active
        )
    {
        Identity storage rec = _agents[agentId];
        return (rec.version, rec.metadataCid, rec.skills, rec.issuer, rec.active);
    }

    function isAgent(string calldata agentId) external view returns (bool) {
        return _agents[agentId].active;
    }

    function metadataOf(string calldata agentId) external view returns (string memory) {
        return _agents[agentId].metadataCid;
    }
}
