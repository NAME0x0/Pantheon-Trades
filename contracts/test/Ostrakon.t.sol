// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {Ostrakon} from "../src/Ostrakon.sol";

contract OstrakonTest is Test {
    Ostrakon internal ostrakon;
    address internal admin = address(0xA11CE);

    function setUp() public {
        ostrakon = new Ostrakon(admin);
    }

    function test_SetWeightUpdatesMapping() public {
        vm.prank(admin);
        ostrakon.setWeight("zeus", 12_500);
        assertEq(ostrakon.weight("zeus"), 12_500);
    }
}
