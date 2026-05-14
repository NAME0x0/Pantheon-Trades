// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {DecisionCourt} from "../src/DecisionCourt.sol";

contract DecisionCourtTest is Test {
    DecisionCourt internal court;
    address internal admin = address(0xA11CE);

    function setUp() public {
        court = new DecisionCourt(admin);
    }

    function test_RecordsDecision() public {
        bytes32 thesisId = keccak256("th-1");
        uint8 approved = court.DECISION_APPROVED();
        vm.prank(admin);
        court.record(thesisId, approved, "OK", "half-Kelly 3%");

        (uint8 decision, string memory code, string memory note, uint64 at) = court.get(thesisId);
        assertEq(decision, approved);
        assertEq(code, "OK");
        assertEq(note, "half-Kelly 3%");
        assertGt(at, 0);
    }
}
