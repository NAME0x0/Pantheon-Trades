// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ITradeProof {
    event TradeRecorded(
        bytes32 indexed tradeId,
        bytes32 indexed thesisId,
        string marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    );

    function record(
        bytes32 tradeId,
        bytes32 thesisId,
        string calldata marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    ) external;

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
        );
}
