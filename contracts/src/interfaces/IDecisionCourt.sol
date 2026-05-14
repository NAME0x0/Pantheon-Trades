// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IDecisionCourt {
    event DecisionRecorded(bytes32 indexed thesisId, uint8 decision, string reasonCode, string note, address indexed by);

    function record(bytes32 thesisId, uint8 decision, string calldata reasonCode, string calldata note) external;
    function get(bytes32 thesisId)
        external
        view
        returns (uint8 decision, string memory reasonCode, string memory note, uint64 recordedAt);
}
