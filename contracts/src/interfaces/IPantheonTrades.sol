// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPantheonTrades {
    event Wired(address indexed contractAddr, bytes32 indexed roleId);

    function snapshot()
        external
        view
        returns (
            address constitution,
            address thesisRegistry,
            address signalRegistry,
            address restraint,
            address noTradeAlpha
        );
}
