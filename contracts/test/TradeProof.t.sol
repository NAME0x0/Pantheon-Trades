// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {TradeProof} from "../src/TradeProof.sol";

contract TradeProofTest is Test {
    TradeProof internal proof;
    address internal admin = address(0xA11CE);

    function setUp() public {
        proof = new TradeProof(admin);
    }

    function test_RecordRoundTrip() public {
        bytes32 tid = keccak256("trade-1");
        bytes32 thid = keccak256("thesis-1");

        vm.prank(admin);
        proof.record(tid, thid, "0xmarket", 0, 300e6, 400_000);

        (
            bytes32 thesisId,
            string memory marketId,
            uint8 direction,
            uint256 sizeUsdc,
            uint256 entryPriceE6,
            uint64 at
        ) = proof.get(tid);
        assertEq(thesisId, thid);
        assertEq(marketId, "0xmarket");
        assertEq(direction, 0);
        assertEq(sizeUsdc, 300e6);
        assertEq(entryPriceE6, 400_000);
        assertGt(at, 0);
    }
}
