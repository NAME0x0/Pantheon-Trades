// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {SignalRegistry} from "../src/SignalRegistry.sol";

contract SignalRegistryTest is Test {
    SignalRegistry internal registry;
    address internal admin = address(0xA11CE);
    address internal stranger = address(0xBEEF);

    function setUp() public {
        registry = new SignalRegistry(admin);
    }

    function test_RecordStoresPayload() public {
        bytes32 sid = keccak256("sig-1");
        bytes32 sh = keccak256("hash-1");

        vm.prank(admin);
        registry.record(sid, sh, "0xmarket", "A");

        SignalRegistry.SignalRecord memory rec = registry.recordOf(sid);
        assertEq(rec.signalHash, sh);
        assertEq(rec.marketId, "0xmarket");
        assertEq(rec.band, "A");
        assertEq(rec.recordedBy, admin);
    }

    function test_RecordRejectsDuplicate() public {
        bytes32 sid = keccak256("sig-2");

        vm.startPrank(admin);
        registry.record(sid, keccak256("a"), "0xmkt", "S");
        vm.expectRevert(abi.encodeWithSelector(SignalRegistry.AlreadyRecorded.selector, sid));
        registry.record(sid, keccak256("b"), "0xmkt", "S");
        vm.stopPrank();
    }

    function test_RecordRejectsEmptyHash() public {
        vm.prank(admin);
        vm.expectRevert(SignalRegistry.EmptyHash.selector);
        registry.record(keccak256("sid"), bytes32(0), "m", "A");
    }

    function test_RecordRequiresRole() public {
        vm.prank(stranger);
        vm.expectRevert();
        registry.record(keccak256("sid"), keccak256("h"), "m", "A");
    }
}
