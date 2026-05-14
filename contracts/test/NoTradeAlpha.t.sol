// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {NoTradeAlpha} from "../src/NoTradeAlpha.sol";

contract NoTradeAlphaTest is Test {
    NoTradeAlpha internal alpha;
    address internal admin = address(0xA11CE);
    address internal stranger = address(0xBEEF);

    function setUp() public {
        alpha = new NoTradeAlpha(admin);
    }

    function test_RecordAccumulates() public {
        vm.startPrank(admin);
        alpha.recordAvoided(keccak256("h1"), "STALENESS", 1_000);
        alpha.recordAvoided(keccak256("h2"), "STALENESS", 2_000);
        alpha.recordAvoided(keccak256("h3"), "EDGE", 500);
        vm.stopPrank();

        assertEq(alpha.reasonCounts("STALENESS"), 2);
        assertEq(alpha.reasonCounts("EDGE"), 1);
        assertEq(alpha.reasonNotional("STALENESS"), 3_000);
        assertEq(alpha.reasonNotional("EDGE"), 500);
        assertEq(alpha.totalAvoidedNotional(), 3_500);
        assertEq(alpha.totalDeclines(), 3);
    }

    function test_RecordRejectsEmptyReason() public {
        vm.prank(admin);
        vm.expectRevert(NoTradeAlpha.EmptyReason.selector);
        alpha.recordAvoided(keccak256("h"), "", 100);
    }

    function test_RecordRequiresRole() public {
        vm.prank(stranger);
        vm.expectRevert();
        alpha.recordAvoided(keccak256("h"), "EDGE", 100);
    }
}
