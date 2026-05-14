// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Bands
/// @notice On-chain mirror of Apollo's band classification thresholds.
library Bands {
    uint16 internal constant S_MIN_EDGE_BPS = 1_500; // 15%
    uint16 internal constant A_MIN_EDGE_BPS = 800;   // 8%
    uint16 internal constant B_MIN_EDGE_BPS = 500;   // 5%
    uint16 internal constant C_MIN_EDGE_BPS = 200;   // 2%

    uint16 internal constant S_MIN_LIQ_BPS = 8_000; // 0.80
    uint16 internal constant A_MIN_LIQ_BPS = 6_000;
    uint16 internal constant B_MIN_LIQ_BPS = 4_000;
    uint16 internal constant C_MIN_LIQ_BPS = 2_000;

    function classify(uint16 edgeAbsBps, uint16 liquidityBps)
        internal
        pure
        returns (bytes1 band)
    {
        if (edgeAbsBps >= S_MIN_EDGE_BPS && liquidityBps >= S_MIN_LIQ_BPS) return "S";
        if (edgeAbsBps >= A_MIN_EDGE_BPS && liquidityBps >= A_MIN_LIQ_BPS) return "A";
        if (edgeAbsBps >= B_MIN_EDGE_BPS && liquidityBps >= B_MIN_LIQ_BPS) return "B";
        if (edgeAbsBps >= C_MIN_EDGE_BPS && liquidityBps >= C_MIN_LIQ_BPS) return "C";
        return "D";
    }

    function isEligibleForBoule(bytes1 band) internal pure returns (bool) {
        return band == bytes1("S") || band == bytes1("A");
    }
}
