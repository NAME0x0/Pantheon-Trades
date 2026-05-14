// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {PantheonConstitution} from "../src/PantheonConstitution.sol";

contract PantheonConstitutionTest is Test {
    PantheonConstitution internal constitution;

    function setUp() public {
        constitution = new PantheonConstitution();
    }

    function test_VersionIsSet() public view {
        assertEq(constitution.VERSION(), "1.0.0");
    }

    function test_ChainIdIsArcTestnet() public view {
        assertEq(constitution.CHAIN_ID(), 5_042_002);
    }

    function test_SealedAtMatchesBlockTimestamp() public view {
        assertEq(constitution.SEALED_AT(), uint64(block.timestamp));
    }

    function test_DeployerIsTestContract() public view {
        assertEq(constitution.DEPLOYER(), address(this));
    }

    function test_SizeWithinLimits_AcceptsValid() public view {
        assertTrue(constitution.isSizeWithinLimits(500)); // 5%
    }

    function test_SizeWithinLimits_RejectsBelowFloor() public view {
        assertFalse(constitution.isSizeWithinLimits(10)); // 0.1% < 0.5% floor
    }

    function test_SizeWithinLimits_RejectsAboveHardCap() public view {
        assertFalse(constitution.isSizeWithinLimits(2_000)); // 20% > 10% hard cap
    }

    function test_SignalAcceptable_PassingSignal() public view {
        assertTrue(
            constitution.isSignalAcceptable({
                edgeAbsBps: 600,
                liquidityBps: 7_000,
                spreadBps: 200,
                stalenessSeconds: 30,
                daysToResolution: 14
            })
        );
    }

    function test_SignalAcceptable_RejectsLowEdge() public view {
        assertFalse(
            constitution.isSignalAcceptable({
                edgeAbsBps: 200,
                liquidityBps: 7_000,
                spreadBps: 200,
                stalenessSeconds: 30,
                daysToResolution: 14
            })
        );
    }

    function test_SignalAcceptable_RejectsStaleData() public view {
        assertFalse(
            constitution.isSignalAcceptable({
                edgeAbsBps: 600,
                liquidityBps: 7_000,
                spreadBps: 200,
                stalenessSeconds: 700,
                daysToResolution: 14
            })
        );
    }

    function test_Snapshot() public view {
        (
            string memory version,
            uint64 chainId,
            uint256 deploymentBlock,
            uint64 sealedAt,
            address deployer
        ) = constitution.snapshot();
        assertEq(version, "1.0.0");
        assertEq(chainId, 5_042_002);
        assertEq(deploymentBlock, block.number);
        assertEq(sealedAt, uint64(block.timestamp));
        assertEq(deployer, address(this));
    }
}
