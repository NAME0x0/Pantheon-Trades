// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IProofOfRestraint {
    event Restrained(
        uint256 indexed proofId,
        bytes32 indexed signalHash,
        string marketId,
        string reasonCode,
        string note,
        address indexed author,
        uint64 recordedAt
    );

    function declineTrade(
        bytes32 signalHash,
        string calldata marketId,
        string calldata reasonCode,
        string calldata note
    ) external returns (uint256 proofId);
}
