// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AgentReputation} from "../src/AgentReputation.sol";

contract AgentReputationTest is Test {
    AgentReputation internal rep;
    address internal admin = address(0xA11CE);

    function setUp() public {
        rep = new AgentReputation(admin);
    }

    function test_UpdateAndGet() public {
        vm.prank(admin);
        rep.update("zeus", 1_800, 11_000, 42);
        (uint256 brier, uint256 cred, uint256 count, uint64 ts) = rep.get("zeus");
        assertEq(brier, 1_800);
        assertEq(cred, 11_000);
        assertEq(count, 42);
        assertGt(ts, 0);
    }
}
