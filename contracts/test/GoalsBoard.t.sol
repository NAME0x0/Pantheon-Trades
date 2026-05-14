// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {GoalsBoard} from "../src/GoalsBoard.sol";

contract GoalsBoardTest is Test {
    GoalsBoard internal board;
    address internal admin = address(0xA11CE);

    function setUp() public {
        board = new GoalsBoard(admin);
    }

    function test_SetAndProgress() public {
        bytes32 goalId = keccak256("daily-bread");
        vm.startPrank(admin);
        board.setGoal(goalId, "Daily Bread", int256(100_000_000), 1);
        board.updateProgress(goalId, int256(60_000_000), 1);
        vm.stopPrank();

        (string memory title, int256 target, int256 current, uint32 horizon, uint8 status, uint64 at) =
            board.get(goalId);
        assertEq(title, "Daily Bread");
        assertEq(target, int256(100_000_000));
        assertEq(current, int256(60_000_000));
        assertEq(horizon, 1);
        assertEq(status, 1);
        assertGt(at, 0);
    }
}
