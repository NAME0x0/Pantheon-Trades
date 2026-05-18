// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {VisitorWitness} from "../src/VisitorWitness.sol";

contract VisitorWitnessTest is Test {
    VisitorWitness internal vw;
    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);

    event Visited(
        uint256 indexed proofId,
        address indexed visitor,
        bytes32 indexed visitHash,
        string  scenario,
        uint64  recordedAt
    );

    function setUp() public {
        vw = new VisitorWitness();
    }

    function test_AssignsMonotonicProofId() public {
        vm.prank(alice);
        uint256 id1 = vw.witness(keccak256("a1"), "demo-approve");
        vm.prank(bob);
        uint256 id2 = vw.witness(keccak256("b1"), "demo-restraint");
        assertEq(id1, 1);
        assertEq(id2, 2);
        assertEq(vw.total(), 2);
    }

    function test_TracksPerAddressVisits() public {
        vm.startPrank(alice);
        vw.witness(keccak256("a1"), "demo");
        vw.witness(keccak256("a2"), "demo");
        vw.witness(keccak256("a3"), "demo");
        vm.stopPrank();
        vm.prank(bob);
        vw.witness(keccak256("b1"), "demo");
        assertEq(vw.visits(alice), 3);
        assertEq(vw.visits(bob), 1);
        assertEq(vw.total(), 4);
    }

    function test_EmitsVisitedEvent() public {
        bytes32 h = keccak256("visit-hash");
        vm.expectEmit(true, true, true, true);
        emit Visited(1, alice, h, "demo-approve", uint64(block.timestamp));
        vm.prank(alice);
        vw.witness(h, "demo-approve");
    }

    function test_RejectsEmptyHash() public {
        vm.expectRevert(VisitorWitness.EmptyHash.selector);
        vm.prank(alice);
        vw.witness(bytes32(0), "demo");
    }

    function test_PermissionlessForAnyCaller() public {
        // Any random address can call — no role gating.
        address random = address(0xDEADBEEF);
        vm.prank(random);
        uint256 id = vw.witness(keccak256("r"), "demo");
        assertEq(id, 1);
        assertEq(vw.visits(random), 1);
    }

    function test_AcceptsEmptyScenarioString() public {
        // Scenario label is optional; only the hash must be non-zero.
        vm.prank(alice);
        uint256 id = vw.witness(keccak256("x"), "");
        assertEq(id, 1);
    }
}
