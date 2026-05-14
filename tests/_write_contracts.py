"""Bulk-write the remaining Solidity contract bodies."""

import os
import sys

ROOT = "D:/Pantheon-Trades/contracts/src"


FILES: dict[str, str] = {}

# ----- erc8004 ---------------------------------------------------------------

FILES["erc8004/IERC8004.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC8004 {
    function isAgent(string calldata agentId) external view returns (bool);
    function metadataOf(string calldata agentId) external view returns (string memory);
}
'''

FILES["erc8004/IdentityRegistry.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC8004} from "./IERC8004.sol";

/// @title IdentityRegistry
/// @notice ERC-8004 agent identity store. Keyed by agent_id; each entry binds
///         a (version, metadataCid, skills, issuer) tuple plus an active bit.
contract IdentityRegistry is AccessControl, IERC8004 {
    bytes32 public constant PASSPORT_ROLE = keccak256("PASSPORT_ROLE");

    struct Identity {
        uint256 version;
        string  metadataCid;
        string[] skills;
        address issuer;
        bool    active;
        uint64  updatedAt;
    }

    mapping(string => Identity) private _agents;

    event Minted(string indexed agentId, uint256 version, string metadataCid, address indexed issuer);
    event Revoked(string indexed agentId, address indexed issuer);

    error EmptyAgentId();
    error VersionMustIncrease();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PASSPORT_ROLE, admin);
    }

    function mint(
        string calldata agentId,
        uint256 version,
        string calldata metadataCid,
        string[] calldata skills
    ) external onlyRole(PASSPORT_ROLE) {
        if (bytes(agentId).length == 0) revert EmptyAgentId();
        Identity storage rec = _agents[agentId];
        if (version <= rec.version) revert VersionMustIncrease();
        rec.version = version;
        rec.metadataCid = metadataCid;
        delete rec.skills;
        for (uint256 i = 0; i < skills.length; ++i) {
            rec.skills.push(skills[i]);
        }
        rec.issuer = msg.sender;
        rec.active = true;
        rec.updatedAt = uint64(block.timestamp);
        emit Minted(agentId, version, metadataCid, msg.sender);
    }

    function revoke(string calldata agentId) external onlyRole(PASSPORT_ROLE) {
        Identity storage rec = _agents[agentId];
        rec.active = false;
        rec.updatedAt = uint64(block.timestamp);
        emit Revoked(agentId, msg.sender);
    }

    function get(string calldata agentId)
        external
        view
        returns (
            uint256 version,
            string memory metadataCid,
            string[] memory skills,
            address issuer,
            bool active
        )
    {
        Identity storage rec = _agents[agentId];
        return (rec.version, rec.metadataCid, rec.skills, rec.issuer, rec.active);
    }

    function isAgent(string calldata agentId) external view returns (bool) {
        return _agents[agentId].active;
    }

    function metadataOf(string calldata agentId) external view returns (string memory) {
        return _agents[agentId].metadataCid;
    }
}
'''

FILES["erc8004/ReputationRegistry.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ReputationRegistry
/// @notice Stores per-agent reputation snapshots (Brier in bps + credibility
///         weight in bps + total prediction count) so any consumer of the
///         ERC-8004 identity can look up live agent quality.
contract ReputationRegistry is AccessControl {
    bytes32 public constant REPUTATION_ROLE = keccak256("REPUTATION_ROLE");

    struct ReputationEntry {
        uint256 brierBps;
        uint256 credibilityBps;
        uint256 predictionCount;
        uint64  updatedAt;
    }

    mapping(string => ReputationEntry) private _entries;

    event Updated(
        string indexed agentId,
        uint256 brierBps,
        uint256 credibilityBps,
        uint256 predictionCount,
        uint64  updatedAt
    );

    error EmptyAgentId();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REPUTATION_ROLE, admin);
    }

    function update(
        string calldata agentId,
        uint256 brierBps,
        uint256 credibilityBps,
        uint256 predictionCount
    ) external onlyRole(REPUTATION_ROLE) {
        if (bytes(agentId).length == 0) revert EmptyAgentId();
        _entries[agentId] = ReputationEntry({
            brierBps: brierBps,
            credibilityBps: credibilityBps,
            predictionCount: predictionCount,
            updatedAt: uint64(block.timestamp)
        });
        emit Updated(agentId, brierBps, credibilityBps, predictionCount, uint64(block.timestamp));
    }

    function get(string calldata agentId)
        external
        view
        returns (uint256 brierBps, uint256 credibilityBps, uint256 predictionCount, uint64 updatedAt)
    {
        ReputationEntry storage rec = _entries[agentId];
        return (rec.brierBps, rec.credibilityBps, rec.predictionCount, rec.updatedAt);
    }
}
'''

FILES["erc8004/ValidationRegistry.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ValidationRegistry
/// @notice External attestations about an ERC-8004 agent. Each call records
///         (agentId, attester, score) so dashboards can show who has audited
///         which agent and what their grade was.
contract ValidationRegistry is AccessControl {
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");

    struct Attestation {
        address attester;
        uint256 scoreBps;
        string  note;
        uint64  at;
    }

    mapping(string => Attestation[]) private _attestations;

    event Attested(string indexed agentId, address indexed attester, uint256 scoreBps, string note);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(VALIDATOR_ROLE, admin);
    }

    function attest(string calldata agentId, uint256 scoreBps, string calldata note)
        external
        onlyRole(VALIDATOR_ROLE)
    {
        _attestations[agentId].push(
            Attestation({
                attester: msg.sender,
                scoreBps: scoreBps,
                note: note,
                at: uint64(block.timestamp)
            })
        );
        emit Attested(agentId, msg.sender, scoreBps, note);
    }

    function count(string calldata agentId) external view returns (uint256) {
        return _attestations[agentId].length;
    }

    function get(string calldata agentId, uint256 index)
        external
        view
        returns (address attester, uint256 scoreBps, string memory note, uint64 at)
    {
        Attestation storage rec = _attestations[agentId][index];
        return (rec.attester, rec.scoreBps, rec.note, rec.at);
    }
}
'''

# ----- governance ------------------------------------------------------------

FILES["governance/RoleManager.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title RoleManager
/// @notice Centralised role administrator. Other Pantheon contracts can read
///         from this to decide whether a caller is authorised.
contract RoleManager is AccessControl {
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }
}
'''

FILES["governance/EmergencyPause.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title EmergencyPause
/// @notice Operator-controlled kill switch. Reads ``paused()`` to decide
///         whether a wired contract should refuse mutating calls.
contract EmergencyPause is AccessControl {
    bytes32 public constant PAUSE_ROLE = keccak256("PAUSE_ROLE");

    bool private _paused;
    string public reason;

    event Paused(address indexed by, string reason);
    event Unpaused(address indexed by);

    error NotPaused();
    error AlreadyPaused();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PAUSE_ROLE, admin);
    }

    function pause(string calldata _reason) external onlyRole(PAUSE_ROLE) {
        if (_paused) revert AlreadyPaused();
        _paused = true;
        reason = _reason;
        emit Paused(msg.sender, _reason);
    }

    function unpause() external onlyRole(PAUSE_ROLE) {
        if (!_paused) revert NotPaused();
        _paused = false;
        delete reason;
        emit Unpaused(msg.sender);
    }

    function paused() external view returns (bool) {
        return _paused;
    }
}
'''

FILES["governance/ZeusMultisig.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ZeusMultisig
/// @notice Minimal M-of-N multisig wrapping calls. Confirmation tally tracked
///         per (target, data, value) tuple; once threshold met the call
///         executes once.
contract ZeusMultisig {
    address[] public signers;
    uint256 public immutable threshold;

    mapping(bytes32 => uint256) public confirmations;
    mapping(bytes32 => mapping(address => bool)) public confirmedBy;
    mapping(bytes32 => bool) public executed;

    event Confirmed(bytes32 indexed callId, address indexed signer, uint256 confirmations);
    event Executed(bytes32 indexed callId, address target, uint256 value);

    error NotSigner();
    error AlreadyConfirmed();
    error AlreadyExecuted();
    error InsufficientConfirmations();

    constructor(address[] memory _signers, uint256 _threshold) {
        require(_threshold > 0 && _threshold <= _signers.length, "bad threshold");
        signers = _signers;
        threshold = _threshold;
    }

    function isSigner(address who) public view returns (bool) {
        for (uint256 i = 0; i < signers.length; ++i) {
            if (signers[i] == who) return true;
        }
        return false;
    }

    function confirm(address target, uint256 value, bytes calldata data) external {
        if (!isSigner(msg.sender)) revert NotSigner();
        bytes32 callId = keccak256(abi.encode(target, value, data));
        if (executed[callId]) revert AlreadyExecuted();
        if (confirmedBy[callId][msg.sender]) revert AlreadyConfirmed();
        confirmedBy[callId][msg.sender] = true;
        confirmations[callId] += 1;
        emit Confirmed(callId, msg.sender, confirmations[callId]);
    }

    function execute(address target, uint256 value, bytes calldata data) external {
        bytes32 callId = keccak256(abi.encode(target, value, data));
        if (executed[callId]) revert AlreadyExecuted();
        if (confirmations[callId] < threshold) revert InsufficientConfirmations();
        executed[callId] = true;
        (bool ok, ) = target.call{value: value}(data);
        require(ok, "call failed");
        emit Executed(callId, target, value);
    }

    receive() external payable {}
}
'''

# ----- top-level contracts ---------------------------------------------------

FILES["AgentPassport.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IdentityRegistry} from "./erc8004/IdentityRegistry.sol";

/// @title AgentPassport
/// @notice Thin Pantheon-flavoured wrapper around the ERC-8004 IdentityRegistry.
///         All storage lives in IdentityRegistry; this contract just exposes
///         the Pantheon-specific deploy + admin events.
contract AgentPassport is IdentityRegistry {
    constructor(address admin) IdentityRegistry(admin) {}
}
'''

FILES["AgentReputation.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReputationRegistry} from "./erc8004/ReputationRegistry.sol";

/// @title AgentReputation
/// @notice Pantheon wrapper around the ERC-8004 ReputationRegistry.
contract AgentReputation is ReputationRegistry {
    constructor(address admin) ReputationRegistry(admin) {}
}
'''

FILES["DecisionCourt.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title DecisionCourt
/// @notice On-chain ledger of Areopagus thesis decisions.
contract DecisionCourt is AccessControl {
    bytes32 public constant COURT_ROLE = keccak256("COURT_ROLE");

    uint8 public constant DECISION_APPROVED = 1;
    uint8 public constant DECISION_REJECTED = 2;
    uint8 public constant DECISION_RESIZED  = 3;

    struct Decision {
        uint8   decision;
        string  reasonCode;
        string  note;
        uint64  recordedAt;
    }

    mapping(bytes32 => Decision) private _decisions;

    event DecisionRecorded(bytes32 indexed thesisId, uint8 decision, string reasonCode, string note, address indexed by);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(COURT_ROLE, admin);
    }

    function record(bytes32 thesisId, uint8 decision, string calldata reasonCode, string calldata note)
        external
        onlyRole(COURT_ROLE)
    {
        _decisions[thesisId] = Decision(decision, reasonCode, note, uint64(block.timestamp));
        emit DecisionRecorded(thesisId, decision, reasonCode, note, msg.sender);
    }

    function get(bytes32 thesisId)
        external
        view
        returns (uint8 decision, string memory reasonCode, string memory note, uint64 recordedAt)
    {
        Decision storage d = _decisions[thesisId];
        return (d.decision, d.reasonCode, d.note, d.recordedAt);
    }
}
'''

FILES["TradeProof.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title TradeProof
/// @notice Stores a compact, verifiable proof of every executed trade.
contract TradeProof is AccessControl {
    bytes32 public constant TRADE_ROLE = keccak256("TRADE_ROLE");

    struct Trade {
        bytes32 thesisId;
        string  marketId;
        uint8   direction;          // 0=YES, 1=NO
        uint256 sizeUsdc6;          // size in USDC with 6 decimals
        uint256 entryPriceE6;       // entry price scaled by 1e6
        uint64  recordedAt;
    }

    mapping(bytes32 => Trade) private _trades;

    event TradeRecorded(
        bytes32 indexed tradeId,
        bytes32 indexed thesisId,
        string marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(TRADE_ROLE, admin);
    }

    function record(
        bytes32 tradeId,
        bytes32 thesisId,
        string calldata marketId,
        uint8 direction,
        uint256 sizeUsdc6,
        uint256 entryPriceE6
    ) external onlyRole(TRADE_ROLE) {
        _trades[tradeId] = Trade({
            thesisId: thesisId,
            marketId: marketId,
            direction: direction,
            sizeUsdc6: sizeUsdc6,
            entryPriceE6: entryPriceE6,
            recordedAt: uint64(block.timestamp)
        });
        emit TradeRecorded(tradeId, thesisId, marketId, direction, sizeUsdc6, entryPriceE6);
    }

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
        )
    {
        Trade storage t = _trades[tradeId];
        return (t.thesisId, t.marketId, t.direction, t.sizeUsdc6, t.entryPriceE6, t.recordedAt);
    }
}
'''

FILES["GoalsBoard.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title GoalsBoard
/// @notice Live Olympus goal progress mirrored on-chain.
contract GoalsBoard is AccessControl {
    bytes32 public constant GOAL_ROLE = keccak256("GOAL_ROLE");

    struct Goal {
        string  title;
        int256  targetE6;
        int256  currentE6;
        uint32  horizonDays;
        uint8   status;     // 0=open, 1=on_track, 2=at_risk, 3=achieved, 4=missed
        uint64  updatedAt;
    }

    mapping(bytes32 => Goal) private _goals;

    event GoalSet(bytes32 indexed goalId, string title, int256 targetE6, uint32 horizonDays);
    event GoalProgress(bytes32 indexed goalId, int256 currentE6, uint8 status);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOAL_ROLE, admin);
    }

    function setGoal(bytes32 goalId, string calldata title, int256 targetE6, uint32 horizonDays)
        external
        onlyRole(GOAL_ROLE)
    {
        Goal storage g = _goals[goalId];
        g.title = title;
        g.targetE6 = targetE6;
        g.horizonDays = horizonDays;
        g.updatedAt = uint64(block.timestamp);
        emit GoalSet(goalId, title, targetE6, horizonDays);
    }

    function updateProgress(bytes32 goalId, int256 currentE6, uint8 status) external onlyRole(GOAL_ROLE) {
        Goal storage g = _goals[goalId];
        g.currentE6 = currentE6;
        g.status = status;
        g.updatedAt = uint64(block.timestamp);
        emit GoalProgress(goalId, currentE6, status);
    }

    function get(bytes32 goalId)
        external
        view
        returns (
            string memory title,
            int256 targetE6,
            int256 currentE6,
            uint32 horizonDays,
            uint8 status,
            uint64 updatedAt
        )
    {
        Goal storage g = _goals[goalId];
        return (g.title, g.targetE6, g.currentE6, g.horizonDays, g.status, g.updatedAt);
    }
}
'''

FILES["StrategyLifecycle.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title StrategyLifecycle
/// @notice On-chain mirror of Moirai's strategy state machine.
contract StrategyLifecycle is AccessControl {
    bytes32 public constant LIFECYCLE_ROLE = keccak256("LIFECYCLE_ROLE");

    uint8 public constant DRAFT       = 0;
    uint8 public constant REGISTERED  = 1;
    uint8 public constant PAPER       = 2;
    uint8 public constant LIVE        = 3;
    uint8 public constant SUSPENDED   = 4;
    uint8 public constant TERMINATED  = 5;

    struct Strategy {
        string  name;
        uint8   state;
        uint64  updatedAt;
    }

    mapping(bytes32 => Strategy) private _strategies;

    event Registered(bytes32 indexed strategyId, string name);
    event StateChanged(bytes32 indexed strategyId, uint8 from_, uint8 to_);
    event Terminated(bytes32 indexed strategyId, string reason);

    error InvalidTransition();
    error AlreadyExists();
    error Unknown();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(LIFECYCLE_ROLE, admin);
    }

    function register(bytes32 strategyId, string calldata name) external onlyRole(LIFECYCLE_ROLE) {
        if (bytes(_strategies[strategyId].name).length != 0) revert AlreadyExists();
        _strategies[strategyId] = Strategy({name: name, state: DRAFT, updatedAt: uint64(block.timestamp)});
        emit Registered(strategyId, name);
    }

    function transition(bytes32 strategyId, uint8 target) external onlyRole(LIFECYCLE_ROLE) {
        Strategy storage s = _strategies[strategyId];
        if (bytes(s.name).length == 0) revert Unknown();
        if (!_isValid(s.state, target)) revert InvalidTransition();
        uint8 from_ = s.state;
        s.state = target;
        s.updatedAt = uint64(block.timestamp);
        emit StateChanged(strategyId, from_, target);
    }

    function terminate(bytes32 strategyId, string calldata reason) external onlyRole(LIFECYCLE_ROLE) {
        Strategy storage s = _strategies[strategyId];
        if (bytes(s.name).length == 0) revert Unknown();
        s.state = TERMINATED;
        s.updatedAt = uint64(block.timestamp);
        emit Terminated(strategyId, reason);
    }

    function state(bytes32 strategyId) external view returns (uint8) {
        return _strategies[strategyId].state;
    }

    function _isValid(uint8 current, uint8 target) internal pure returns (bool) {
        if (target == TERMINATED) return true; // terminate from anywhere
        if (current == DRAFT)      return target == REGISTERED;
        if (current == REGISTERED) return target == PAPER;
        if (current == PAPER)      return target == LIVE || target == SUSPENDED;
        if (current == LIVE)       return target == SUSPENDED;
        if (current == SUSPENDED)  return target == LIVE;
        return false;
    }
}
'''

FILES["Olympus.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Olympus
/// @notice System-state machine mirroring services/olympus/src/olympus/state.py.
contract Olympus is AccessControl {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    uint8 public constant STANDBY  = 0;
    uint8 public constant ACTIVE   = 1;
    uint8 public constant DEGRADED = 2;
    uint8 public constant PAUSED   = 3;
    uint8 public constant RECOVERY = 4;

    uint8 public state = STANDBY;

    event StateChanged(uint8 from_, uint8 to_, string reason, uint64 at);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(OPERATOR_ROLE, admin);
    }

    function transition(uint8 target, string calldata reason) external onlyRole(OPERATOR_ROLE) {
        require(_canMove(state, target), "invalid transition");
        uint8 from_ = state;
        state = target;
        emit StateChanged(from_, target, reason, uint64(block.timestamp));
    }

    function acceptsNewTrades() external view returns (bool) {
        return state == ACTIVE;
    }

    function _canMove(uint8 current, uint8 target) internal pure returns (bool) {
        if (current == STANDBY)  return target == ACTIVE;
        if (current == ACTIVE)   return target == DEGRADED || target == PAUSED;
        if (current == DEGRADED) return target == ACTIVE   || target == PAUSED;
        if (current == PAUSED)   return target == RECOVERY || target == STANDBY;
        if (current == RECOVERY) return target == ACTIVE   || target == STANDBY;
        return false;
    }
}
'''

FILES["Ostrakon.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Ostrakon
/// @notice On-chain mirror of agent credibility weights.
contract Ostrakon is AccessControl {
    bytes32 public constant SCORER_ROLE = keccak256("SCORER_ROLE");

    mapping(string => uint256) public weights;   // basis points: 10000 = 1.0
    mapping(string => uint64)  public updatedAt;

    event WeightUpdated(string indexed agentId, uint256 credibilityBps);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCORER_ROLE, admin);
    }

    function setWeight(string calldata agentId, uint256 credibilityBps) external onlyRole(SCORER_ROLE) {
        weights[agentId] = credibilityBps;
        updatedAt[agentId] = uint64(block.timestamp);
        emit WeightUpdated(agentId, credibilityBps);
    }

    function weight(string calldata agentId) external view returns (uint256) {
        return weights[agentId];
    }
}
'''

FILES["StakingVault.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title StakingVault
/// @notice USDC-denominated stake per agent address. Slashable by SLASHER_ROLE.
contract StakingVault is AccessControl {
    bytes32 public constant SLASHER_ROLE = keccak256("SLASHER_ROLE");

    IERC20 public immutable asset;
    mapping(address => uint256) public balances;
    address public immutable treasury;

    event Staked(address indexed agent, uint256 amount);
    event Unstaked(address indexed agent, uint256 amount);
    event Slashed(address indexed agent, uint256 amount, string reason);

    constructor(IERC20 _asset, address _treasury, address admin) {
        asset = _asset;
        treasury = _treasury;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SLASHER_ROLE, admin);
    }

    function stake(uint256 amount) external {
        require(amount > 0, "zero");
        require(asset.transferFrom(msg.sender, address(this), amount), "transfer failed");
        balances[msg.sender] += amount;
        emit Staked(msg.sender, amount);
    }

    function unstake(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient stake");
        balances[msg.sender] -= amount;
        require(asset.transfer(msg.sender, amount), "transfer failed");
        emit Unstaked(msg.sender, amount);
    }

    function slash(address agent, uint256 amount, string calldata reason) external onlyRole(SLASHER_ROLE) {
        require(balances[agent] >= amount, "insufficient balance");
        balances[agent] -= amount;
        require(asset.transfer(treasury, amount), "transfer failed");
        emit Slashed(agent, amount, reason);
    }

    function balanceOf(address agent) external view returns (uint256) {
        return balances[agent];
    }
}
'''

FILES["ExecutionVault.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title ExecutionVault
/// @notice Holds the operator's USDC float backing Strategos live trades.
contract ExecutionVault is AccessControl {
    bytes32 public constant EXECUTOR_ROLE = keccak256("EXECUTOR_ROLE");

    IERC20 public immutable asset;

    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);

    constructor(IERC20 _asset, address admin) {
        asset = _asset;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(EXECUTOR_ROLE, admin);
    }

    function deposit(uint256 amount) external {
        require(asset.transferFrom(msg.sender, address(this), amount), "transferFrom failed");
        emit Deposited(msg.sender, amount);
    }

    function withdraw(address to, uint256 amount) external onlyRole(EXECUTOR_ROLE) {
        require(asset.transfer(to, amount), "transfer failed");
        emit Withdrawn(to, amount);
    }

    function balance() external view returns (uint256) {
        return asset.balanceOf(address(this));
    }
}
'''

FILES["CounterfactualOracle.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title CounterfactualOracle
/// @notice Persistent record of Elysium counterfactual studies.
contract CounterfactualOracle is AccessControl {
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");

    struct Entry {
        string  label;
        int256  deltaPnlUsdc6;
        address author;
        uint64  recordedAt;
    }

    mapping(bytes32 => Entry) private _entries;

    event CounterfactualRecorded(bytes32 indexed key, string label, int256 deltaPnlUsdc6, address indexed author);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ORACLE_ROLE, admin);
    }

    function record(bytes32 key, string calldata label, int256 deltaPnlUsdc6) external onlyRole(ORACLE_ROLE) {
        _entries[key] = Entry({
            label: label,
            deltaPnlUsdc6: deltaPnlUsdc6,
            author: msg.sender,
            recordedAt: uint64(block.timestamp)
        });
        emit CounterfactualRecorded(key, label, deltaPnlUsdc6, msg.sender);
    }

    function get(bytes32 key)
        external
        view
        returns (string memory label, int256 deltaPnlUsdc6, address author, uint64 recordedAt)
    {
        Entry storage e = _entries[key];
        return (e.label, e.deltaPnlUsdc6, e.author, e.recordedAt);
    }
}
'''

FILES["Elysium.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Elysium
/// @notice On-chain registry of published backtest runs.
contract Elysium is AccessControl {
    bytes32 public constant PUBLISHER_ROLE = keccak256("PUBLISHER_ROLE");

    struct Run {
        int256  realisedPnlUsdc6;
        uint256 nTrades;
        uint256 sharpeE6;
        uint64  publishedAt;
    }

    mapping(bytes32 => Run) private _runs;

    event BacktestPublished(bytes32 indexed runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PUBLISHER_ROLE, admin);
    }

    function publish(bytes32 runId, int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6)
        external
        onlyRole(PUBLISHER_ROLE)
    {
        _runs[runId] = Run({
            realisedPnlUsdc6: realisedPnlUsdc6,
            nTrades: nTrades,
            sharpeE6: sharpeE6,
            publishedAt: uint64(block.timestamp)
        });
        emit BacktestPublished(runId, realisedPnlUsdc6, nTrades, sharpeE6);
    }

    function get(bytes32 runId)
        external
        view
        returns (int256 realisedPnlUsdc6, uint256 nTrades, uint256 sharpeE6, uint64 publishedAt)
    {
        Run storage r = _runs[runId];
        return (r.realisedPnlUsdc6, r.nTrades, r.sharpeE6, r.publishedAt);
    }
}
'''

FILES["Underworld.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title Underworld
/// @notice On-chain log of post-mortem filings.
contract Underworld is AccessControl {
    bytes32 public constant SCRIBE_ROLE = keccak256("SCRIBE_ROLE");

    uint8 public constant OUTCOME_WIN  = 1;
    uint8 public constant OUTCOME_LOSS = 2;
    uint8 public constant OUTCOME_PUSH = 3;

    struct PostMortem {
        uint8    outcome;
        string   primaryFailure;
        string[] brokenAssumptions;
        address  author;
        uint64   at;
    }

    mapping(bytes32 => PostMortem) private _filings;

    event PostMortemFiled(bytes32 indexed thesisId, uint8 outcome, string primaryFailure, address indexed by);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SCRIBE_ROLE, admin);
    }

    function file(
        bytes32 thesisId,
        uint8 outcome,
        string calldata primaryFailure,
        string[] calldata brokenAssumptions
    ) external onlyRole(SCRIBE_ROLE) {
        PostMortem storage pm = _filings[thesisId];
        pm.outcome = outcome;
        pm.primaryFailure = primaryFailure;
        delete pm.brokenAssumptions;
        for (uint256 i = 0; i < brokenAssumptions.length; ++i) {
            pm.brokenAssumptions.push(brokenAssumptions[i]);
        }
        pm.author = msg.sender;
        pm.at = uint64(block.timestamp);
        emit PostMortemFiled(thesisId, outcome, primaryFailure, msg.sender);
    }

    function get(bytes32 thesisId)
        external
        view
        returns (uint8 outcome, string memory primaryFailure, string[] memory brokenAssumptions, address author, uint64 at)
    {
        PostMortem storage pm = _filings[thesisId];
        return (pm.outcome, pm.primaryFailure, pm.brokenAssumptions, pm.author, pm.at);
    }
}
'''

FILES["Parthenon.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {ThesisRegistry} from "./ThesisRegistry.sol";

/// @title Parthenon
/// @notice High-level facade — the Pantheon dashboard imports this and reads
///         the underlying registry plus a top-level "archive index" pointer.
contract Parthenon is AccessControl {
    bytes32 public constant CURATOR_ROLE = keccak256("CURATOR_ROLE");

    ThesisRegistry public immutable registry;
    string public latestIndexCid;

    event IndexUpdated(string indexed indexCid, address indexed by);

    constructor(ThesisRegistry _registry, address admin) {
        registry = _registry;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CURATOR_ROLE, admin);
    }

    function setIndex(string calldata indexCid) external onlyRole(CURATOR_ROLE) {
        latestIndexCid = indexCid;
        emit IndexUpdated(indexCid, msg.sender);
    }
}
'''

FILES["PantheonTrades.sol"] = '''// SPDX-License-Identifier: MIT
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
'''


def main() -> int:
    for relpath, content in FILES.items():
        path = os.path.join(ROOT, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"wrote {relpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
