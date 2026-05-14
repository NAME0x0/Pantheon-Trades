// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {ProofOfRestraint} from "../src/ProofOfRestraint.sol";

contract ProofOfRestraintTest is Test {
    ProofOfRestraint internal por;
    address internal admin = address(0xA11CE);
    address internal stranger = address(0xBEEF);

    function setUp() public {
        por = new ProofOfRestraint(admin);
    }

    function test_DeclineAssignsMonotonicProofId() public {
        vm.startPrank(admin);
        uint256 id1 = por.declineTrade(keccak256("h1"), "m", "STALENESS", "stale");
        uint256 id2 = por.declineTrade(keccak256("h2"), "m", "EDGE", "low edge");
        vm.stopPrank();
        assertEq(id1, 1);
        assertEq(id2, 2);
        assertEq(por.nextProofId(), 2);
    }

    function test_RecordOfStoresFields() public {
        vm.prank(admin);
        uint256 id = por.declineTrade(keccak256("h"), "mkt", "EDGE", "low edge");
        ProofOfRestraint.RestraintRecord memory rec = por.recordOf(id);
        assertEq(rec.proofId, id);
        assertEq(rec.signalHash, keccak256("h"));
        assertEq(rec.marketId, "mkt");
        assertEq(rec.reasonCode, "EDGE");
        assertEq(rec.author, admin);
    }

    function test_DeclineRejectsEmptyReason() public {
        vm.prank(admin);
        vm.expectRevert(ProofOfRestraint.EmptyReason.selector);
        por.declineTrade(keccak256("h"), "m", "", "");
    }

    function test_DeclineRejectsEmptyHash() public {
        vm.prank(admin);
        vm.expectRevert(ProofOfRestraint.EmptyHash.selector);
        por.declineTrade(bytes32(0), "m", "EDGE", "");
    }

    function test_DeclineRequiresRole() public {
        vm.prank(stranger);
        vm.expectRevert();
        por.declineTrade(keccak256("h"), "m", "EDGE", "");
    }
}
