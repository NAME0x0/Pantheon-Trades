// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {ThesisRegistry} from "../src/ThesisRegistry.sol";
import {IThesisRegistry} from "../src/interfaces/IThesisRegistry.sol";

contract ThesisRegistryTest is Test {
    ThesisRegistry internal registry;

    address internal admin = address(0xA11CE);
    address internal stranger = address(0xBEEF);

    function setUp() public {
        registry = new ThesisRegistry(admin);
    }

    function test_AnchorRecordsRoot() public {
        bytes32 root = keccak256("test-root");

        vm.prank(admin);
        registry.anchor("thesis", "QmManifestCid1", root);

        assertEq(registry.rootOf("QmManifestCid1"), root);
    }

    function test_AnchorEmitsEvent() public {
        bytes32 root = keccak256("event-root");
        bytes32 manifestId = keccak256(bytes("QmEvent"));

        vm.expectEmit(true, false, true, true);
        emit IThesisRegistry.Anchored({
            manifestId: manifestId,
            kind: "thesis",
            manifestCid: "QmEvent",
            merkleRoot: root,
            anchoredBy: admin,
            anchoredAt: uint64(block.timestamp)
        });

        vm.prank(admin);
        registry.anchor("thesis", "QmEvent", root);
    }

    function test_AnchorRejectsEmptyCid() public {
        vm.prank(admin);
        vm.expectRevert(ThesisRegistry.EmptyCid.selector);
        registry.anchor("thesis", "", keccak256("r"));
    }

    function test_AnchorRejectsZeroRoot() public {
        vm.prank(admin);
        vm.expectRevert(ThesisRegistry.ZeroRoot.selector);
        registry.anchor("thesis", "QmZero", bytes32(0));
    }

    function test_AnchorRejectsDuplicate() public {
        vm.startPrank(admin);
        registry.anchor("thesis", "QmDup", keccak256("a"));
        vm.expectRevert(
            abi.encodeWithSelector(ThesisRegistry.AlreadyAnchored.selector, "QmDup")
        );
        registry.anchor("thesis", "QmDup", keccak256("b"));
        vm.stopPrank();
    }

    function test_AnchorRejectsUnauthorisedCaller() public {
        vm.prank(stranger);
        vm.expectRevert();
        registry.anchor("thesis", "QmAuth", keccak256("r"));
    }

    function test_VerifyProofRoundTrip() public {
        // Two-leaf tree, sorted-pair hashing.
        bytes32 leafA = keccak256("leaf-a");
        bytes32 leafB = keccak256("leaf-b");
        bytes32 root = leafA < leafB ? keccak256(abi.encodePacked(leafA, leafB))
                                     : keccak256(abi.encodePacked(leafB, leafA));

        vm.prank(admin);
        registry.anchor("thesis", "QmTree", root);

        bytes32[] memory proof = new bytes32[](1);
        proof[0] = leafB;
        assertTrue(registry.verifyProof("QmTree", leafA, proof));

        proof[0] = leafA;
        assertTrue(registry.verifyProof("QmTree", leafB, proof));
    }

    function test_VerifyProofUnknownManifest() public view {
        bytes32[] memory proof = new bytes32[](0);
        assertFalse(registry.verifyProof("QmMissing", keccak256("x"), proof));
    }

    function test_RecordOfReturnsFullRecord() public {
        bytes32 root = keccak256("rec-root");

        vm.prank(admin);
        registry.anchor("outcome", "QmRecord", root);

        ThesisRegistry.AnchorRecord memory rec = registry.recordOf("QmRecord");
        assertEq(rec.merkleRoot, root);
        assertEq(rec.kind, "outcome");
        assertEq(rec.manifestCid, "QmRecord");
        assertEq(rec.anchoredBy, admin);
        assertEq(rec.anchoredAt, uint64(block.timestamp));
    }

    function test_ThesisHashMatchesPythonFormat() public view {
        // Off-chain: keccak256("thesis-0|0xprobe|0.550000|YES")
        bytes32 expected = keccak256("thesis-0|0xprobe|0.550000|YES");
        bytes32 actual = registry.thesisHash("thesis-0", "0xprobe", 550_000, "YES");
        assertEq(actual, expected);
    }
}
