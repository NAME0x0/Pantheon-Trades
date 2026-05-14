// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {StakingVault} from "../src/StakingVault.sol";
import {MockUsdc} from "./ExecutionVault.t.sol";

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract StakingVaultTest is Test {
    MockUsdc internal usdc;
    StakingVault internal vault;
    address internal admin = address(0xA11CE);
    address internal treasury = address(0xBABE);
    address internal agent = address(0xBEEF);

    function setUp() public {
        usdc = new MockUsdc();
        vault = new StakingVault(IERC20(address(usdc)), treasury, admin);
        usdc.mint(agent, 1_000e6);
    }

    function test_StakeUnstakeSlash() public {
        vm.startPrank(agent);
        usdc.approve(address(vault), 500e6);
        vault.stake(500e6);
        vm.stopPrank();
        assertEq(vault.balanceOf(agent), 500e6);

        vm.prank(agent);
        vault.unstake(200e6);
        assertEq(vault.balanceOf(agent), 300e6);

        vm.prank(admin);
        vault.slash(agent, 100e6, "constitutional_breach");
        assertEq(vault.balanceOf(agent), 200e6);
        assertEq(usdc.balanceOf(treasury), 100e6);
    }
}
