// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {ProofOfRestraint} from "../src/ProofOfRestraint.sol";

/// @title TransferRestraintAdmin
/// @notice Migrates the DEFAULT_ADMIN_ROLE on a deployed ProofOfRestraint
///         from the single-key deployer to a Gnosis Safe multisig (or any
///         other contract / account). The current admin then revokes its
///         own role so the flagship contract is no longer controlled by
///         a single private key.
///
/// @dev Usage:
///
///     forge script script/TransferRestraintAdmin.s.sol:TransferRestraintAdmin \
///         --rpc-url https://rpc.testnet.arc.network \
///         --broadcast \
///         --sig "run(address,address)" \
///         <PROOF_OF_RESTRAINT_ADDRESS> <NEW_ADMIN_SAFE>
///
/// The script GRANTS the new admin first, then REVOKES the deployer's
/// own admin role. Order matters — if we revoked first, the contract
/// would be admin-less and unrecoverable.
contract TransferRestraintAdmin is Script {
    function run(address proofOfRestraint, address newAdmin) external {
        require(proofOfRestraint != address(0), "POR address required");
        require(newAdmin != address(0), "new admin required");

        uint256 pk = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);

        ProofOfRestraint por = ProofOfRestraint(proofOfRestraint);

        bytes32 DEFAULT_ADMIN_ROLE = bytes32(0);
        bytes32 RESTRAINT_ROLE = por.RESTRAINT_ROLE();

        vm.startBroadcast(pk);

        // 1. Grant the multisig both roles. Order matters — admin
        //    first so it can self-manage if anything goes sideways.
        por.grantRole(DEFAULT_ADMIN_ROLE, newAdmin);
        por.grantRole(RESTRAINT_ROLE, newAdmin);

        // 2. Revoke the deployer's roles. The contract is now solely
        //    controlled by `newAdmin`.
        por.revokeRole(RESTRAINT_ROLE, deployer);
        por.revokeRole(DEFAULT_ADMIN_ROLE, deployer);

        vm.stopBroadcast();
    }
}
