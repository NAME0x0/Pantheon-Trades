// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Hashing
/// @notice Shared hashing helpers that match Parthenon's off-chain scheme.
library Hashing {
    /// @notice Compute the canonical thesis identifier matching
    ///         ``parthenon.hash.thesis_hash`` in the Python services.
    function thesisHash(
        string memory thesisId,
        string memory marketId,
        uint256 councilProbabilityE6,
        string memory direction
    ) internal pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                thesisId, "|", marketId, "|", _formatE6(councilProbabilityE6), "|", direction
            )
        );
    }

    function signalHash(bytes memory canonicalJson) internal pure returns (bytes32) {
        return keccak256(canonicalJson);
    }

    function _formatE6(uint256 e6) private pure returns (string memory) {
        uint256 integerPart = e6 / 1_000_000;
        uint256 fractionalPart = e6 % 1_000_000;
        return string.concat(_toString(integerPart), ".", _padFractional(fractionalPart));
    }

    function _padFractional(uint256 value) private pure returns (string memory) {
        bytes memory out = new bytes(6);
        for (uint256 i = 6; i > 0; --i) {
            out[i - 1] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return string(out);
    }

    function _toString(uint256 value) private pure returns (string memory) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) { ++digits; temp /= 10; }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            --digits;
            buffer[digits] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}
