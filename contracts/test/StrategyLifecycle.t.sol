// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {StrategyLifecycle} from "../src/StrategyLifecycle.sol";

contract StrategyLifecycleTest is Test {
    StrategyLifecycle internal lifecycle;
    address internal admin = address(0xA11CE);

    function setUp() public {
        lifecycle = new StrategyLifecycle(admin);
    }

    function test_DraftToLive() public {
        bytes32 strategyId = keccak256("momentum-v1");
        vm.startPrank(admin);
        lifecycle.register(strategyId, "momentum-v1");
        lifecycle.transition(strategyId, lifecycle.REGISTERED());
        lifecycle.transition(strategyId, lifecycle.PAPER());
        lifecycle.transition(strategyId, lifecycle.LIVE());
        vm.stopPrank();
        assertEq(lifecycle.state(strategyId), lifecycle.LIVE());
    }

    function test_InvalidTransitionReverts() public {
        bytes32 strategyId = keccak256("strat");
        uint8 live = lifecycle.LIVE();
        vm.startPrank(admin);
        lifecycle.register(strategyId, "strat");
        vm.expectRevert(StrategyLifecycle.InvalidTransition.selector);
        lifecycle.transition(strategyId, live);
        vm.stopPrank();
    }

    function test_TerminateFromAnyState() public {
        bytes32 strategyId = keccak256("strat");
        vm.startPrank(admin);
        lifecycle.register(strategyId, "strat");
        lifecycle.terminate(strategyId, "operator kill");
        vm.stopPrank();
        assertEq(lifecycle.state(strategyId), lifecycle.TERMINATED());
    }
}
