// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PantheonTrades
/// @notice Read-only facade wiring every Pantheon contract address into one
///         on-chain registry. Useful for the dashboard's "system" view and
///         for off-chain clients that prefer one source of truth.
contract PantheonTrades {
    address public immutable constitution;
    address public immutable thesisRegistry;
    address public immutable signalRegistry;
    address public immutable restraint;
    address public immutable noTradeAlpha;
    address public immutable olympus;
    address public immutable ostrakon;
    address public immutable parthenon;
    address public immutable executionVault;
    address public immutable stakingVault;
    address public immutable strategyLifecycle;
    address public immutable agentPassport;
    address public immutable agentReputation;
    address public immutable decisionCourt;
    address public immutable tradeProof;
    address public immutable goalsBoard;
    address public immutable elysium;
    address public immutable underworld;
    address public immutable counterfactualOracle;

    event PantheonAssembled(address indexed deployer);

    constructor(
        address[19] memory wiring
    ) {
        constitution         = wiring[0];
        thesisRegistry       = wiring[1];
        signalRegistry       = wiring[2];
        restraint            = wiring[3];
        noTradeAlpha         = wiring[4];
        olympus              = wiring[5];
        ostrakon             = wiring[6];
        parthenon            = wiring[7];
        executionVault       = wiring[8];
        stakingVault         = wiring[9];
        strategyLifecycle    = wiring[10];
        agentPassport        = wiring[11];
        agentReputation      = wiring[12];
        decisionCourt        = wiring[13];
        tradeProof           = wiring[14];
        goalsBoard           = wiring[15];
        elysium              = wiring[16];
        underworld           = wiring[17];
        counterfactualOracle = wiring[18];
        emit PantheonAssembled(msg.sender);
    }

    function snapshot()
        external
        view
        returns (
            address _constitution,
            address _thesisRegistry,
            address _signalRegistry,
            address _restraint,
            address _noTradeAlpha
        )
    {
        return (constitution, thesisRegistry, signalRegistry, restraint, noTradeAlpha);
    }
}
