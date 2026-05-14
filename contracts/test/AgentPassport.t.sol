// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AgentPassport} from "../src/AgentPassport.sol";
import {IdentityRegistry} from "../src/erc8004/IdentityRegistry.sol";

contract AgentPassportTest is Test {
    AgentPassport internal passport;
    address internal admin = address(0xA11CE);

    function setUp() public {
        passport = new AgentPassport(admin);
    }

    function test_MintAndGet() public {
        string[] memory skills = new string[](2);
        skills[0] = "bull_advocate";
        skills[1] = "fundamentals";

        vm.prank(admin);
        passport.mint("ares", 1, "QmAresMeta", skills);

        (uint256 version, string memory cid, string[] memory readSkills, address issuer, bool active) =
            passport.get("ares");
        assertEq(version, 1);
        assertEq(cid, "QmAresMeta");
        assertEq(readSkills.length, 2);
        assertEq(issuer, admin);
        assertTrue(active);
    }

    function test_VersionMustIncrease() public {
        string[] memory skills = new string[](0);
        vm.startPrank(admin);
        passport.mint("ares", 2, "v2", skills);
        vm.expectRevert(IdentityRegistry.VersionMustIncrease.selector);
        passport.mint("ares", 2, "v2-again", skills);
        vm.stopPrank();
    }

    function test_RevokeFlipsActive() public {
        string[] memory skills = new string[](0);
        vm.startPrank(admin);
        passport.mint("ares", 1, "QmAres", skills);
        passport.revoke("ares");
        vm.stopPrank();
        (, , , , bool active) = passport.get("ares");
        assertFalse(active);
    }
}
