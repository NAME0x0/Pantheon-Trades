// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ValidationRegistry
/// @notice External attestations about an ERC-8004 agent. Each call records
///         (agentId, attester, score) so dashboards can show who has audited
///         which agent and what their grade was.
contract ValidationRegistry is AccessControl {
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");

    struct Attestation {
        address attester;
        uint256 scoreBps;
        string  note;
        uint64  at;
    }

    mapping(string => Attestation[]) private _attestations;

    event Attested(string indexed agentId, address indexed attester, uint256 scoreBps, string note);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(VALIDATOR_ROLE, admin);
    }

    function attest(string calldata agentId, uint256 scoreBps, string calldata note)
        external
        onlyRole(VALIDATOR_ROLE)
    {
        _attestations[agentId].push(
            Attestation({
                attester: msg.sender,
                scoreBps: scoreBps,
                note: note,
                at: uint64(block.timestamp)
            })
        );
        emit Attested(agentId, msg.sender, scoreBps, note);
    }

    function count(string calldata agentId) external view returns (uint256) {
        return _attestations[agentId].length;
    }

    function get(string calldata agentId, uint256 index)
        external
        view
        returns (address attester, uint256 scoreBps, string memory note, uint64 at)
    {
        Attestation storage rec = _attestations[agentId][index];
        return (rec.attester, rec.scoreBps, rec.note, rec.at);
    }
}
