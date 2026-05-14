// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ICounterfactualOracle {
    event CounterfactualRecorded(bytes32 indexed key, string label, int256 deltaPnlUsdc6, address indexed author);

    function record(bytes32 key, string calldata label, int256 deltaPnlUsdc6) external;
    function get(bytes32 key)
        external
        view
        returns (string memory label, int256 deltaPnlUsdc6, address author, uint64 recordedAt);
}
