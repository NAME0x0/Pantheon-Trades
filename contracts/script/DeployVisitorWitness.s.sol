// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {VisitorWitness} from "../src/VisitorWitness.sol";

/// @title DeployVisitorWitness
/// @notice Deploys the permissionless visitor-witness contract used by the
///         website "Run on Arc" demo. No constructor args. After deploy:
///         export VISITOR_WITNESS_ADDRESS=<address>
///         and set NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS in apps/web/.env
contract DeployVisitorWitness is Script {
    function run() external returns (VisitorWitness witness) {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);
        console2.log("Deployer:", deployer);

        vm.startBroadcast(pk);
        witness = new VisitorWitness();
        vm.stopBroadcast();

        console2.log("VisitorWitness:", address(witness));
    }
}
