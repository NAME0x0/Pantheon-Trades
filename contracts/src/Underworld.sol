// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Underworld
/// @notice On-chain log of post-mortem filings.
contract Underworld is AccessControl {
    bytes32 public constant SCRIBE_ROLE = keccak256("SCRIBE_ROLE");

    uint8 public constant OUTCOME_WIN  = 1;
    uint8 public constant OUTCOME_LOSS = 2;
    uint8 public constant OUTCOME_PUSH = 3;

    struct PostMortem {
        uint8    outcome;
        string   primaryFailure;
        string[] brokenAssumptions;
        address  author;
        uint64   at;
    }

    mapping(bytes32 => PostMortem) private _filings;

    event PostMortemFiled(bytes32 indexed thesisId, uint8 outcome, string primaryFailure, address indexed by);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCRIBE_ROLE, admin);
    }

    function file(
        bytes32 thesisId,
        uint8 outcome,
        string calldata primaryFailure,
        string[] calldata brokenAssumptions
    ) external onlyRole(SCRIBE_ROLE) {
        PostMortem storage pm = _filings[thesisId];
        pm.outcome = outcome;
        pm.primaryFailure = primaryFailure;
        delete pm.brokenAssumptions;
        for (uint256 i = 0; i < brokenAssumptions.length; ++i) {
            pm.brokenAssumptions.push(brokenAssumptions[i]);
        }
        pm.author = msg.sender;
        pm.at = uint64(block.timestamp);
        emit PostMortemFiled(thesisId, outcome, primaryFailure, msg.sender);
    }

    function get(bytes32 thesisId)
        external
        view
        returns (uint8 outcome, string memory primaryFailure, string[] memory brokenAssumptions, address author, uint64 at)
    {
        PostMortem storage pm = _filings[thesisId];
        return (pm.outcome, pm.primaryFailure, pm.brokenAssumptions, pm.author, pm.at);
    }
}
