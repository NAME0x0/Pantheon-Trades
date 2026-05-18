// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title VisitorWitness
/// @notice Permissionless on-chain receipt that a visitor ran a Pantheon
///         demo from the website. Anyone may call `witness` from any
///         wallet — the contract simply assigns a monotonic id, tallies
///         per-address visits, and emits a `Visited` event. The web
///         dashboard scans these events to render a live "visitors who
///         ran the demo" feed alongside the council's own restraint feed.
///
/// @dev    Append-only. No admin. No state mutation beyond increments.
///         Intended for testnet traction; the contract has no privileged
///         role, no upgrade path, and no economic value.
contract VisitorWitness {
    uint256 public total;
    mapping(address => uint256) public visits;

    event Visited(
        uint256 indexed proofId,
        address indexed visitor,
        bytes32 indexed visitHash,
        string  scenario,
        uint64  recordedAt
    );

    error EmptyHash();

    /// @notice Record that the caller ran a Pantheon demo. The visitHash
    ///         is a client-side digest of (address, scenario, timestamp)
    ///         so the same visitor can record multiple unique runs.
    /// @param  visitHash    keccak digest computed by the dapp
    /// @param  scenario     human-readable label ("council-deliberation",
    ///                      "proof-of-restraint", "backtest-replay", etc.)
    function witness(bytes32 visitHash, string calldata scenario)
        external
        returns (uint256 proofId)
    {
        if (visitHash == bytes32(0)) revert EmptyHash();
        unchecked {
            proofId = ++total;
            visits[msg.sender] += 1;
        }
        emit Visited(proofId, msg.sender, visitHash, scenario, uint64(block.timestamp));
    }
}
