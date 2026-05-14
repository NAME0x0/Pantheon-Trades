// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {PantheonTrades} from "../src/PantheonTrades.sol";

contract PantheonTradesTest is Test {
    function test_SnapshotReturnsConstructorAddresses() public {
        address[19] memory wiring;
        for (uint256 i = 0; i < wiring.length; ++i) {
            wiring[i] = address(uint160(i + 1));
        }
        PantheonTrades pantheon = new PantheonTrades(wiring);
        (
            address constitution,
            address thesisRegistry,
            address signalRegistry,
            address restraint,
            address noTradeAlpha
        ) = pantheon.snapshot();
        assertEq(constitution, address(1));
        assertEq(thesisRegistry, address(2));
        assertEq(signalRegistry, address(3));
        assertEq(restraint, address(4));
        assertEq(noTradeAlpha, address(5));
    }
}
