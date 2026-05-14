// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IUnderworld {
    event PostMortemFiled(bytes32 indexed thesisId, uint8 outcome, string primaryFailure, address indexed by);

    function file(
        bytes32 thesisId,
        uint8 outcome,
        string calldata primaryFailure,
        string[] calldata brokenAssumptions
    ) external;
}
