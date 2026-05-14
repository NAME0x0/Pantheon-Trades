// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ISignalRegistry {
    event SignalRecorded(
        bytes32 indexed signalId,
        bytes32 signalHash,
        string marketId,
        string band,
        address indexed recordedBy,
        uint64 recordedAt
    );

    function record(bytes32 signalId, bytes32 signalHash, string calldata marketId, string calldata band) external;
}
