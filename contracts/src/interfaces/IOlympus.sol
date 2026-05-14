// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IOlympus {
    event StateChanged(uint8 from_, uint8 to_, string reason, uint64 at);

    function transition(uint8 target, string calldata reason) external;
    function state() external view returns (uint8);
    function acceptsNewTrades() external view returns (bool);
}
