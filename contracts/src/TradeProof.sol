// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title TradeProof
/// @notice Stores a compact, verifiable proof of every executed trade.
contract TradeProof is AccessControl {
    bytes32 public constant TRADE_ROLE = keccak256("TRADE_ROLE");

    struct Trade {
        bytes32 thesisId;
        string  marketId;
        uint8   direction;          // 0=YES, 1=NO
        uint256 sizeUsdc6;          // size in USDC with 6 decimals
        uint256 entryPriceE6;       // entry price scaled by 1e6
        uint64  recordedAt;
    }

    mapping(bytes32 => Trade) private _trades;

    event TradeRecorded(
        bytes32 indexed tradeId,
        bytes32 indexed thesisId,
        string marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(TRADE_ROLE, admin);
    }

    function record(
        bytes32 tradeId,
        bytes32 thesisId,
        string calldata marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    ) external onlyRole(TRADE_ROLE) {
        _trades[tradeId] = Trade({
            thesisId: thesisId,
            marketId: marketId,
            direction: direction,
            sizeUsdc6: sizeUsdc6,
            entryPriceE6: entryPriceE6,
            recordedAt: uint64(block.timestamp)
        });
        emit TradeRecorded(tradeId, thesisId, marketId, direction, sizeUsdc6, entryPriceE6);
    }

    function get(bytes32 tradeId)
        external
        view
        returns (
            bytes32 thesisId,
            string memory marketId,
            uint8 direction,
            uint256 sizeUsdc6,
            uint256 entryPriceE6,
            uint64 recordedAt
        )
    {
        Trade storage t = _trades[tradeId];
        return (t.thesisId, t.marketId, t.direction, t.sizeUsdc6, t.entryPriceE6, t.recordedAt);
    }
}
