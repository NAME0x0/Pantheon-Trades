// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {ExecutionVault} from "../src/ExecutionVault.sol";

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// Minimal mock ERC20 for unit tests.
contract MockUsdc is IERC20 {
    string public name = "Mock USDC";
    string public symbol = "USDC";
    uint8 public decimals = 6;
    uint256 public override totalSupply;
    mapping(address => uint256) public override balanceOf;
    mapping(address => mapping(address => uint256)) public override allowance;

    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}

contract ExecutionVaultTest is Test {
    MockUsdc internal usdc;
    ExecutionVault internal vault;
    address internal admin = address(0xA11CE);
    address internal user = address(0xBEEF);

    function setUp() public {
        usdc = new MockUsdc();
        vault = new ExecutionVault(IERC20(address(usdc)), admin);
        usdc.mint(user, 1_000e6);
    }

    function test_DepositAndWithdraw() public {
        vm.startPrank(user);
        usdc.approve(address(vault), 100e6);
        vault.deposit(100e6);
        vm.stopPrank();
        assertEq(vault.balance(), 100e6);

        vm.prank(admin);
        vault.withdraw(user, 60e6);
        assertEq(vault.balance(), 40e6);
        assertEq(usdc.balanceOf(user), 960e6);
    }
}
