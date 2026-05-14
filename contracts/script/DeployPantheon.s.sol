// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {PantheonConstitution} from "../src/PantheonConstitution.sol";
import {ThesisRegistry} from "../src/ThesisRegistry.sol";

/// @title DeployPantheon
/// @notice Deploys PantheonConstitution + ThesisRegistry to the active RPC.
///
/// Usage:
///   forge script script/DeployPantheon.s.sol:DeployPantheon \
///     --rpc-url arc_testnet \
///     --private-key $PRIVATE_KEY \
///     --broadcast -vvv
///
/// PantheonConstitution is immutable; ThesisRegistry is constructed with
/// the deployer as initial admin + anchor role. Rotate via grantRole after
/// confirming the off-chain anchor service holds the production key.
contract DeployPantheon is Script {
    function run()
        external
        returns (PantheonConstitution constitution, ThesisRegistry registry)
    {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address admin = vm.addr(pk);

        console2.log("=== Pantheon deploy ===");
        console2.log("Deployer:", admin);
        console2.log("Chain id:", block.chainid);

        vm.startBroadcast(pk);

        constitution = new PantheonConstitution();
        console2.log("PantheonConstitution:", address(constitution));
        console2.log("  VERSION:", constitution.VERSION());
        console2.log("  CHAIN_ID:", constitution.CHAIN_ID());
        console2.log("  SEALED_AT:", constitution.SEALED_AT());

        registry = new ThesisRegistry(admin);
        console2.log("ThesisRegistry:", address(registry));
        console2.log("  admin:", admin);

        vm.stopBroadcast();
    }
}
