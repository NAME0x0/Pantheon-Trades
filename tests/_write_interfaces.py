"""One-shot script to bulk-write all Solidity interface stubs."""

import os
import sys

ROOT = "D:/Pantheon-Trades/contracts/src/interfaces"


INTERFACES: dict[str, str] = {}

INTERFACES["IAgentPassport.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentPassport {
    event PassportMinted(string indexed agentId, uint256 version, string metadataCid, address indexed issuer);
    event PassportRevoked(string indexed agentId, address indexed issuer);

    function mint(string calldata agentId, uint256 version, string calldata metadataCid, string[] calldata skills) external;
    function revoke(string calldata agentId) external;
    function get(string calldata agentId)
        external
        view
        returns (uint256 version, string memory metadataCid, string[] memory skills, address issuer, bool active);
}
'''

INTERFACES["IAgentReputation.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAgentReputation {
    event ReputationUpdated(string indexed agentId, uint256 brierBps, uint256 credibilityBps, uint256 predictionCount);

    function update(string calldata agentId, uint256 brierBps, uint256 credibilityBps, uint256 predictionCount) external;
    function get(string calldata agentId)
        external
        view
        returns (uint256 brierBps, uint256 credibilityBps, uint256 predictionCount, uint64 updatedAt);
}
'''

INTERFACES["ICounterfactualOracle.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ICounterfactualOracle {
    event CounterfactualRecorded(bytes32 indexed key, string label, int256 deltaPnlUsdc6, address indexed author);

    function record(bytes32 key, string calldata label, int256 deltaPnlUsdc6) external;
    function get(bytes32 key)
        external
        view
        returns (string memory label, int256 deltaPnlUsdc6, address author, uint64 recordedAt);
}
'''

INTERFACES["IDecisionCourt.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IDecisionCourt {
    event DecisionRecorded(bytes32 indexed thesisId, uint8 decision, string reasonCode, string note, address indexed by);

    function record(bytes32 thesisId, uint8 decision, string calldata reasonCode, string calldata note) external;
    function get(bytes32 thesisId)
        external
        view
        returns (uint8 decision, string memory reasonCode, string memory note, uint64 recordedAt);
}
'''

INTERFACES["IElysium.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IElysium {
    event BacktestPublished(bytes32 indexed runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6);

    function publish(bytes32 runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6) external;
    function get(bytes32 runId)
        external
        view
        returns (int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6, uint64 publishedAt);
}
'''

INTERFACES["IExecutionVault.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IExecutionVault {
    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);

    function deposit(uint256 amount) external;
    function withdraw(address to, uint256 amount) external;
    function balance() external view returns (uint256);
}
'''

INTERFACES["IGoalsBoard.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IGoalsBoard {
    event GoalSet(bytes32 indexed goalId, string title, int256 targetE6, uint32 horizonDays);
    event GoalProgress(bytes32 indexed goalId, int256 currentE6, uint8 status);

    function setGoal(bytes32 goalId, string calldata title, int256 targetE6, uint32 horizonDays) external;
    function updateProgress(bytes32 goalId, int256 currentE6, uint8 status) external;
}
'''

INTERFACES["IOlympus.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IOlympus {
    event StateChanged(uint8 from_, uint8 to_, string reason, uint64 at);

    function transition(uint8 target, string calldata reason) external;
    function state() external view returns (uint8);
    function acceptsNewTrades() external view returns (bool);
}
'''

INTERFACES["IOstrakon.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IOstrakon {
    event WeightUpdated(string indexed agentId, uint256 credibilityBps);

    function setWeight(string calldata agentId, uint256 credibilityBps) external;
    function weight(string calldata agentId) external view returns (uint256);
}
'''

INTERFACES["IPantheonTrades.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPantheonTrades {
    event Wired(address indexed contractAddr, bytes32 indexed roleId);

    function snapshot()
        external
        view
        returns (
            address constitution,
            address thesisRegistry,
            address signalRegistry,
            address restraint,
            address noTradeAlpha
        );
}
'''

INTERFACES["IStakingVault.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IStakingVault {
    event Staked(address indexed agent, uint256 amount);
    event Unstaked(address indexed agent, uint256 amount);
    event Slashed(address indexed agent, uint256 amount, string reason);

    function stake(uint256 amount) external;
    function unstake(uint256 amount) external;
    function slash(address agent, uint256 amount, string calldata reason) external;
    function balanceOf(address agent) external view returns (uint256);
}
'''

INTERFACES["IStrategyLifecycle.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IStrategyLifecycle {
    event StrategyRegistered(bytes32 indexed strategyId, string name);
    event StateChanged(bytes32 indexed strategyId, uint8 from_, uint8 to_);
    event StrategyTerminated(bytes32 indexed strategyId, string reason);

    function register(bytes32 strategyId, string calldata name) external;
    function transition(bytes32 strategyId, uint8 target) external;
    function terminate(bytes32 strategyId, string calldata reason) external;
    function state(bytes32 strategyId) external view returns (uint8);
}
'''

INTERFACES["ITradeProof.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ITradeProof {
    event TradeRecorded(
        bytes32 indexed tradeId,
        bytes32 indexed thesisId,
        string marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    );

    function record(
        bytes32 tradeId,
        bytes32 thesisId,
        string calldata marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    ) external;

    function get(bytes32 tradeId)
        external
        view
        returns (
            bytes32 thesisId,
            string memory marketId,
            uint8 direction,
            uint256 sizeUsdc6,
            uint256 entryPriceE6,
            uint64 recordedAt
        );
}
'''

INTERFACES["IUnderworld.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IUnderworld {
    event PostMortemFiled(bytes32 indexed thesisId, uint8 outcome, string primaryFailure, address indexed by);

    function file(
        bytes32 thesisId,
        uint8 outcome,
        string calldata primaryFailure,
        string[] calldata brokenAssumptions
    ) external;
}
'''

INTERFACES["INoTradeAlpha.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface INoTradeAlpha {
    event AvoidedTrade(bytes32 indexed signalHash, string reasonCode, uint256 avoidedNotional, address indexed author, uint64 recordedAt);
    function recordAvoided(bytes32 signalHash, string calldata reasonCode, uint256 avoidedNotional) external;
}
'''

INTERFACES["ISignalRegistry.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ISignalRegistry {
    event SignalRecorded(
        bytes32 indexed signalId,
        bytes32 signalHash,
        string marketId,
        string band,
        address indexed recordedBy,
        uint64 recordedAt
    );

    function record(bytes32 signalId, bytes32 signalHash, string calldata marketId, string calldata band) external;
}
'''

INTERFACES["IProofOfRestraint.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IProofOfRestraint {
    event Restrained(
        uint256 indexed proofId,
        bytes32 indexed signalHash,
        string marketId,
        string reasonCode,
        string note,
        address indexed author,
        uint64 recordedAt
    );

    function declineTrade(
        bytes32 signalHash,
        string calldata marketId,
        string calldata reasonCode,
        string calldata note
    ) external returns (uint256 proofId);
}
'''


def main() -> int:
    os.makedirs(ROOT, exist_ok=True)
    for name, content in INTERFACES.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
