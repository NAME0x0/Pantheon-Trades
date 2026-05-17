// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {PantheonConstitution} from "../src/PantheonConstitution.sol";

/// @notice Halmos symbolic checks for PantheonConstitution.
///
/// Run with `just halmos`. Each ``check_*`` function is executed
/// symbolically; assertions must hold for every legal input.
contract PantheonConstitutionSymbolic is Test {
    PantheonConstitution private c;

    function setUp() public {
        c = new PantheonConstitution();
    }

    /// Soft caps must be tighter than their corresponding hard caps —
    /// otherwise the soft cap is meaningless.
    function check_soft_caps_tighter_than_hard() public view {
        assert(c.MAX_POSITION_PCT_BPS() <= c.MAX_POSITION_HARD_BPS());
        assert(c.MAX_SPREAD_BPS() <= c.MAX_SPREAD_HARD_BPS());
        assert(c.MAX_STALENESS_SECONDS() <= c.MAX_STALENESS_HARD_SECONDS());
    }

    /// Resolution-time window must be non-degenerate: min < max.
    function check_resolution_window_nondegenerate() public view {
        assert(c.MIN_DAYS_TO_RESOLUTION() < c.MAX_DAYS_TO_RESOLUTION());
    }

    /// Minimum position threshold must be at least 1bp and never
    /// exceed the soft cap.
    function check_position_floor_below_caps() public view {
        assert(c.MIN_POSITION_THRESHOLD_BPS() >= 1);
        assert(c.MIN_POSITION_THRESHOLD_BPS() <= c.MAX_POSITION_PCT_BPS());
    }

    /// Half-Kelly invariant — the fraction must be exactly 5000 bps.
    /// Constitutional, never to drift.
    function check_kelly_is_half() public view {
        assert(c.KELLY_FRACTION_BPS() == 5_000);
    }

    /// isSizeWithinLimits must accept the floor and reject anything
    /// below it.
    function check_size_floor_boundary(uint16 size) public view {
        if (size < c.MIN_POSITION_THRESHOLD_BPS()) {
            assert(!c.isSizeWithinLimits(size));
        }
    }

    /// isSizeWithinLimits must reject anything above the hard cap.
    function check_size_ceiling_boundary(uint16 size) public view {
        if (size > c.MAX_POSITION_HARD_BPS()) {
            assert(!c.isSizeWithinLimits(size));
        }
    }

    /// isSignalAcceptable must be monotonic in edge — bigger edge can
    /// only flip a previously-acceptable signal AWAY from acceptance
    /// if some OTHER input simultaneously degraded. Holding the rest
    /// fixed, more edge must not turn a YES into a NO.
    function check_signal_acceptance_monotonic_in_edge(
        uint16 edgeA,
        uint16 edgeB,
        uint16 liq,
        uint16 spread,
        uint16 staleness,
        uint16 days_
    ) public view {
        if (edgeA <= edgeB) {
            bool ok_a = c.isSignalAcceptable(edgeA, liq, spread, staleness, days_);
            bool ok_b = c.isSignalAcceptable(edgeB, liq, spread, staleness, days_);
            // If A is acceptable, so must B (more edge, same everything else).
            if (ok_a) assert(ok_b);
        }
    }

    /// Total exposure can never be less than max single-position size,
    /// otherwise no diversified book is possible.
    function check_portfolio_room_for_positions() public view {
        // Even in the worst case where every open position is at
        // MAX_POSITION_PCT_BPS, total exposure cap must allow at
        // least two positions.
        assert(c.MAX_TOTAL_EXPOSURE_BPS() >= 2 * c.MAX_POSITION_PCT_BPS());
    }
}
