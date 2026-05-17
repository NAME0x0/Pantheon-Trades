// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ProofOfRestraint} from "../src/ProofOfRestraint.sol";

/// @notice Halmos symbolic checks for ProofOfRestraint.
///
/// Halmos (a16z, MIT, https://github.com/a16z/halmos) executes any
/// function whose name starts with ``check_`` symbolically — every
/// input is treated as an unknown the SMT solver can pick to violate
/// the assertion. A passing run is a proof; a failing run yields a
/// concrete counter-example.
///
/// Run with:
///     just halmos
/// or:
///     cd contracts && uvx halmos
contract ProofOfRestraintSymbolic is Test {
    ProofOfRestraint private por;
    address private admin = address(0xA11CE);

    function setUp() public {
        por = new ProofOfRestraint(admin);
    }

    // --- Invariants ----------------------------------------------------

    /// proofId must strictly increase: nextProofId never decreases or
    /// repeats a previously-assigned id.
    function check_proof_id_monotonic(
        bytes32 hash1,
        bytes32 hash2,
        string calldata market1,
        string calldata market2,
        string calldata reason1,
        string calldata reason2
    ) public {
        // Filter degenerate inputs the contract refuses.
        vm.assume(hash1 != bytes32(0));
        vm.assume(hash2 != bytes32(0));
        vm.assume(bytes(reason1).length > 0);
        vm.assume(bytes(reason2).length > 0);

        vm.prank(admin);
        uint256 id1 = por.declineTrade(hash1, market1, reason1, "");
        vm.prank(admin);
        uint256 id2 = por.declineTrade(hash2, market2, reason2, "");

        // Monotonicity.
        assert(id2 > id1);
        assert(id1 + 1 == id2);
    }

    /// Records are append-only: storing a proof and then reading it
    /// back yields exactly the inputs the caller supplied.
    function check_record_integrity(
        bytes32 hash,
        string calldata market,
        string calldata reason
    ) public {
        vm.assume(hash != bytes32(0));
        vm.assume(bytes(reason).length > 0);

        vm.prank(admin);
        uint256 id = por.declineTrade(hash, market, reason, "");

        ProofOfRestraint.RestraintRecord memory r = por.recordOf(id);
        assert(r.proofId == id);
        assert(r.signalHash == hash);
        assert(keccak256(bytes(r.marketId)) == keccak256(bytes(market)));
        assert(keccak256(bytes(r.reasonCode)) == keccak256(bytes(reason)));
        assert(r.author == admin);
    }

    /// Only RESTRAINT_ROLE holders can write. Any other caller must
    /// revert.
    function check_only_role_can_write(
        address attacker,
        bytes32 hash,
        string calldata market,
        string calldata reason
    ) public {
        vm.assume(hash != bytes32(0));
        vm.assume(bytes(reason).length > 0);
        vm.assume(attacker != admin);
        vm.assume(!por.hasRole(por.RESTRAINT_ROLE(), attacker));

        vm.prank(attacker);
        // Halmos: must revert — wrap the call so we can assert.
        bool reverted = false;
        try por.declineTrade(hash, market, reason, "") returns (uint256) {
            reverted = false;
        } catch {
            reverted = true;
        }
        assert(reverted);
    }

    /// Empty hash or empty reason must revert.
    function check_input_validation(
        bytes32 hash,
        string calldata reason
    ) public {
        bool reverted = false;
        vm.prank(admin);
        try por.declineTrade(hash, "any-market", reason, "") returns (uint256) {
            reverted = false;
        } catch {
            reverted = true;
        }
        bool expectedRevert = (hash == bytes32(0)) || (bytes(reason).length == 0);
        if (expectedRevert) {
            assert(reverted);
        }
        // The complementary direction (valid inputs must succeed) is
        // already covered by check_record_integrity above.
    }
}
