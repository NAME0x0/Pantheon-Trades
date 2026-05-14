// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PantheonConstitution
/// @notice Immutable constitutional limits for the Pantheon Trades system.
/// @dev Every constant here is the on-chain mirror of the values enforced
///      off-chain by Areopagus (see docs/RISK_POLICY.md and docs/CONSTITUTION.md).
///      Once deployed this contract MUST NEVER be modified — there is no
///      owner, no proxy, and no upgrade path. All limits are public and
///      readable so any party can audit a proposed trade against the
///      published constitution.
contract PantheonConstitution {
    // ----- Version ----------------------------------------------------------

    string public constant VERSION = "1.0.0";

    // ----- Council quorum ---------------------------------------------------

    /// @notice Minimum number of non-abstaining council votes required.
    uint8 public constant MIN_QUORUM = 7;

    /// @notice Minimum weighted-confidence APPROVE share required to pass.
    /// @dev Encoded in basis points (10000 = 100%).
    uint16 public constant APPROVAL_THRESHOLD_BPS = 6_000; // 60%

    // ----- Per-trade sizing -------------------------------------------------

    /// @notice Maximum single-position size as a fraction of book equity (bps).
    uint16 public constant MAX_POSITION_PCT_BPS = 500; // 5%

    /// @notice Hard cap that no resize is ever allowed to exceed (bps).
    uint16 public constant MAX_POSITION_HARD_BPS = 1_000; // 10%

    /// @notice Smallest position the system will ever open (bps).
    /// @dev Below this floor the gas + slippage cost dominates the edge.
    uint16 public constant MIN_POSITION_THRESHOLD_BPS = 50; // 0.5%

    // ----- Portfolio limits -------------------------------------------------

    uint8 public constant MAX_OPEN_POSITIONS = 10;
    uint16 public constant MAX_TOTAL_EXPOSURE_BPS = 4_000; // 40%
    uint16 public constant MAX_CATEGORY_EXPOSURE_BPS = 1_500; // 15%

    // ----- Signal quality gates --------------------------------------------

    uint16 public constant MIN_EDGE_BPS = 500; // 5%
    uint16 public constant MIN_CONFIDENCE_BPS = 6_500; // 65%
    uint16 public constant MIN_LIQUIDITY_BPS = 5_000; // 50%
    uint16 public constant MAX_SPREAD_BPS = 800; // 8%
    uint16 public constant MAX_SPREAD_HARD_BPS = 1_200; // 12%
    uint16 public constant MAX_STALENESS_SECONDS = 300;
    uint16 public constant MAX_STALENESS_HARD_SECONDS = 600;
    uint16 public constant MIN_DAYS_TO_RESOLUTION = 2;
    uint16 public constant MAX_DAYS_TO_RESOLUTION = 90;

    // ----- Kelly sizing -----------------------------------------------------

    /// @notice Pantheon always uses half-Kelly, never full Kelly (bps).
    uint16 public constant KELLY_FRACTION_BPS = 5_000; // 50%

    // ----- Chain identity ---------------------------------------------------

    /// @notice Arc Testnet chain id this constitution was authored for.
    uint64 public constant CHAIN_ID = 5_042_002;

    // ----- Block-time anchor ------------------------------------------------

    /// @notice Block number at which this constitution was first deployed.
    uint256 public immutable DEPLOYMENT_BLOCK;

    /// @notice Address of the deployer; recorded for provenance only.
    address public immutable DEPLOYER;

    /// @notice Solidity timestamp at which the constitution was sealed.
    uint64 public immutable SEALED_AT;

    event ConstitutionSealed(
        address indexed deployer, uint256 indexed block_, uint64 sealedAt, string version
    );

    constructor() {
        DEPLOYMENT_BLOCK = block.number;
        DEPLOYER = msg.sender;
        SEALED_AT = uint64(block.timestamp);
        emit ConstitutionSealed(msg.sender, block.number, uint64(block.timestamp), VERSION);
    }

    // ----- Audit helpers ----------------------------------------------------

    /// @notice Compact snapshot used by indexers + the dashboard.
    function snapshot()
        external
        view
        returns (
            string memory version,
            uint64 chainId,
            uint256 deploymentBlock,
            uint64 sealedAt,
            address deployer
        )
    {
        return (VERSION, CHAIN_ID, DEPLOYMENT_BLOCK, SEALED_AT, DEPLOYER);
    }

    /// @notice True iff the proposed size fits inside every per-trade cap.
    /// @param proposedSizeBps Size in basis points (10000 = 100%).
    function isSizeWithinLimits(uint16 proposedSizeBps) external pure returns (bool) {
        return proposedSizeBps >= MIN_POSITION_THRESHOLD_BPS
            && proposedSizeBps <= MAX_POSITION_HARD_BPS;
    }

    /// @notice True iff the signal-quality gates would clear for these inputs.
    function isSignalAcceptable(
        uint16 edgeAbsBps,
        uint16 liquidityBps,
        uint16 spreadBps,
        uint16 stalenessSeconds,
        uint16 daysToResolution
    ) external pure returns (bool) {
        return edgeAbsBps >= MIN_EDGE_BPS && liquidityBps >= MIN_LIQUIDITY_BPS
            && spreadBps <= MAX_SPREAD_HARD_BPS && stalenessSeconds <= MAX_STALENESS_HARD_SECONDS
            && daysToResolution >= MIN_DAYS_TO_RESOLUTION && daysToResolution <= MAX_DAYS_TO_RESOLUTION;
    }
}
