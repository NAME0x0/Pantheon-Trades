// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {NoTradeAlpha} from "../src/NoTradeAlpha.sol";
import {ProofOfRestraint} from "../src/ProofOfRestraint.sol";
import {SignalRegistry} from "../src/SignalRegistry.sol";

/// @title DeployRestraint
/// @notice Deploys SignalRegistry + ProofOfRestraint + NoTradeAlpha for the
///         Areopagus on-chain witness pipeline.
contract DeployRestraint is Script {
    function run()
        external
        returns (SignalRegistry signals, ProofOfRestraint restraint, NoTradeAlpha alpha)
    {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address admin = vm.addr(pk);
        console2.log("Deployer:", admin);

        vm.startBroadcast(pk);
        signals = new SignalRegistry(admin);
        restraint = new ProofOfRestraint(admin);
        alpha = new NoTradeAlpha(admin);
        vm.stopBroadcast();

        console2.log("SignalRegistry:   ", address(signals));
        console2.log("ProofOfRestraint: ", address(restraint));
        console2.log("NoTradeAlpha:     ", address(alpha));
    }
}
