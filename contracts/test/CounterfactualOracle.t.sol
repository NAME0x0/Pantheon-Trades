// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {CounterfactualOracle} from "../src/CounterfactualOracle.sol";

contract CounterfactualOracleTest is Test {
    CounterfactualOracle internal oracle;
    address internal admin = address(0xA11CE);

    function setUp() public {
        oracle = new CounterfactualOracle(admin);
    }

    function test_RecordAndGet() public {
        bytes32 key = keccak256("quarter-kelly");
        vm.prank(admin);
        oracle.record(key, "quarter_kelly", int256(-1_234_000));

        (string memory label, int256 delta, address author, uint64 at) = oracle.get(key);
        assertEq(label, "quarter_kelly");
        assertEq(delta, int256(-1_234_000));
        assertEq(author, admin);
        assertGt(at, 0);
    }
}
