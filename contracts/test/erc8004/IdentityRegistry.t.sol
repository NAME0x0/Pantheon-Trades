// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {IdentityRegistry} from "../../src/erc8004/IdentityRegistry.sol";

contract IdentityRegistryTest is Test {
    IdentityRegistry internal registry;
    address internal admin = address(0xA11CE);

    function setUp() public {
        registry = new IdentityRegistry(admin);
    }

    function test_IsAgentReflectsActive() public {
        assertFalse(registry.isAgent("zeus"));
        string[] memory skills = new string[](1);
        skills[0] = "constitutional";

        vm.prank(admin);
        registry.mint("zeus", 1, "QmZeusMeta", skills);
        assertTrue(registry.isAgent("zeus"));
        assertEq(registry.metadataOf("zeus"), "QmZeusMeta");

        vm.prank(admin);
        registry.revoke("zeus");
        assertFalse(registry.isAgent("zeus"));
    }
}
