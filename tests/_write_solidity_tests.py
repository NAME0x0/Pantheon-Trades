"""Bulk-fill smoke tests for every Solidity contract that lacks one."""

import os
import sys

ROOT = "D:/Pantheon-Trades/contracts/test"

FILES: dict[str, str] = {}

FILES["AgentPassport.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AgentPassport} from "../src/AgentPassport.sol";

contract AgentPassportTest is Test {
    AgentPassport internal passport;
    address internal admin = address(0xA11CE);

    function setUp() public {
        passport = new AgentPassport(admin);
    }

    function test_MintAndGet() public {
        string[] memory skills = new string[](2);
        skills[0] = "bull_advocate";
        skills[1] = "fundamentals";

        vm.prank(admin);
        passport.mint("ares", 1, "QmAresMeta", skills);

        (uint256 version, string memory cid, string[] memory readSkills, address issuer, bool active) =
            passport.get("ares");
        assertEq(version, 1);
        assertEq(cid, "QmAresMeta");
        assertEq(readSkills.length, 2);
        assertEq(issuer, admin);
        assertTrue(active);
    }

    function test_VersionMustIncrease() public {
        string[] memory skills = new string[](0);
        vm.startPrank(admin);
        passport.mint("ares", 2, "v2", skills);
        vm.expectRevert(AgentPassport.VersionMustIncrease.selector);
        passport.mint("ares", 2, "v2-again", skills);
        vm.stopPrank();
    }

    function test_RevokeFlipsActive() public {
        string[] memory skills = new string[](0);
        vm.startPrank(admin);
        passport.mint("ares", 1, "QmAres", skills);
        passport.revoke("ares");
        vm.stopPrank();
        (, , , , bool active) = passport.get("ares");
        assertFalse(active);
    }
}
'''

FILES["AgentReputation.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {AgentReputation} from "../src/AgentReputation.sol";

contract AgentReputationTest is Test {
    AgentReputation internal rep;
    address internal admin = address(0xA11CE);

    function setUp() public {
        rep = new AgentReputation(admin);
    }

    function test_UpdateAndGet() public {
        vm.prank(admin);
        rep.update("zeus", 1_800, 11_000, 42);
        (uint256 brier, uint256 cred, uint256 count, uint64 ts) = rep.get("zeus");
        assertEq(brier, 1_800);
        assertEq(cred, 11_000);
        assertEq(count, 42);
        assertGt(ts, 0);
    }
}
'''

FILES["CounterfactualOracle.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {CounterfactualOracle} from "../src/CounterfactualOracle.sol";

contract CounterfactualOracleTest is Test {
    CounterfactualOracle internal oracle;
    address internal admin = address(0xA11CE);

    function setUp() public {
        oracle = new CounterfactualOracle(admin);
    }

    function test_RecordAndGet() public {
        bytes32 key = keccak256("quarter-kelly");
        vm.prank(admin);
        oracle.record(key, "quarter_kelly", int256(-1_234_000));

        (string memory label, int256 delta, address author, uint64 at) = oracle.get(key);
        assertEq(label, "quarter_kelly");
        assertEq(delta, int256(-1_234_000));
        assertEq(author, admin);
        assertGt(at, 0);
    }
}
'''

FILES["DecisionCourt.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {DecisionCourt} from "../src/DecisionCourt.sol";

contract DecisionCourtTest is Test {
    DecisionCourt internal court;
    address internal admin = address(0xA11CE);

    function setUp() public {
        court = new DecisionCourt(admin);
    }

    function test_RecordsDecision() public {
        bytes32 thesisId = keccak256("th-1");
        vm.prank(admin);
        court.record(thesisId, court.DECISION_APPROVED(), "OK", "half-Kelly 3%");

        (uint8 decision, string memory code, string memory note, uint64 at) = court.get(thesisId);
        assertEq(decision, court.DECISION_APPROVED());
        assertEq(code, "OK");
        assertEq(note, "half-Kelly 3%");
        assertGt(at, 0);
    }
}
'''

FILES["erc8004/IdentityRegistry.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {IdentityRegistry} from "../../src/erc8004/IdentityRegistry.sol";

contract IdentityRegistryTest is Test {
    IdentityRegistry internal registry;
    address internal admin = address(0xA11CE);

    function setUp() public {
        registry = new IdentityRegistry(admin);
    }

    function test_IsAgentReflectsActive() public {
        assertFalse(registry.isAgent("zeus"));
        string[] memory skills = new string[](1);
        skills[0] = "constitutional";

        vm.prank(admin);
        registry.mint("zeus", 1, "QmZeusMeta", skills);
        assertTrue(registry.isAgent("zeus"));
        assertEq(registry.metadataOf("zeus"), "QmZeusMeta");

        vm.prank(admin);
        registry.revoke("zeus");
        assertFalse(registry.isAgent("zeus"));
    }
}
'''

FILES["ExecutionVault.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {ExecutionVault} from "../src/ExecutionVault.sol";

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// Minimal mock ERC20 for unit tests.
contract MockUsdc is IERC20 {
    string public name = "Mock USDC";
    string public symbol = "USDC";
    uint8 public decimals = 6;
    uint256 public override totalSupply;
    mapping(address => uint256) public override balanceOf;
    mapping(address => mapping(address => uint256)) public override allowance;

    function mint(address to, uint256 amount) external {
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}

contract ExecutionVaultTest is Test {
    MockUsdc internal usdc;
    ExecutionVault internal vault;
    address internal admin = address(0xA11CE);
    address internal user = address(0xBEEF);

    function setUp() public {
        usdc = new MockUsdc();
        vault = new ExecutionVault(IERC20(address(usdc)), admin);
        usdc.mint(user, 1_000e6);
    }

    function test_DepositAndWithdraw() public {
        vm.startPrank(user);
        usdc.approve(address(vault), 100e6);
        vault.deposit(100e6);
        vm.stopPrank();
        assertEq(vault.balance(), 100e6);

        vm.prank(admin);
        vault.withdraw(user, 60e6);
        assertEq(vault.balance(), 40e6);
        assertEq(usdc.balanceOf(user), 960e6);
    }
}
'''

FILES["GoalsBoard.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {GoalsBoard} from "../src/GoalsBoard.sol";

contract GoalsBoardTest is Test {
    GoalsBoard internal board;
    address internal admin = address(0xA11CE);

    function setUp() public {
        board = new GoalsBoard(admin);
    }

    function test_SetAndProgress() public {
        bytes32 goalId = keccak256("daily-bread");
        vm.startPrank(admin);
        board.setGoal(goalId, "Daily Bread", int256(100_000_000), 1);
        board.updateProgress(goalId, int256(60_000_000), 1);
        vm.stopPrank();

        (string memory title, int256 target, int256 current, uint32 horizon, uint8 status, uint64 at) =
            board.get(goalId);
        assertEq(title, "Daily Bread");
        assertEq(target, int256(100_000_000));
        assertEq(current, int256(60_000_000));
        assertEq(horizon, 1);
        assertEq(status, 1);
        assertGt(at, 0);
    }
}
'''

FILES["Ostrakon.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {Ostrakon} from "../src/Ostrakon.sol";

contract OstrakonTest is Test {
    Ostrakon internal ostrakon;
    address internal admin = address(0xA11CE);

    function setUp() public {
        ostrakon = new Ostrakon(admin);
    }

    function test_SetWeightUpdatesMapping() public {
        vm.prank(admin);
        ostrakon.setWeight("zeus", 12_500);
        assertEq(ostrakon.weight("zeus"), 12_500);
    }
}
'''

FILES["PantheonTrades.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {PantheonTrades} from "../src/PantheonTrades.sol";

contract PantheonTradesTest is Test {
    function test_SnapshotReturnsConstructorAddresses() public {
        address[19] memory wiring;
        for (uint256 i = 0; i < wiring.length; ++i) {
            wiring[i] = address(uint160(i + 1));
        }
        PantheonTrades pantheon = new PantheonTrades(wiring);
        (
            address constitution,
            address thesisRegistry,
            address signalRegistry,
            address restraint,
            address noTradeAlpha
        ) = pantheon.snapshot();
        assertEq(constitution, address(1));
        assertEq(thesisRegistry, address(2));
        assertEq(signalRegistry, address(3));
        assertEq(restraint, address(4));
        assertEq(noTradeAlpha, address(5));
    }
}
'''

FILES["StakingVault.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {StakingVault} from "../src/StakingVault.sol";
import {MockUsdc} from "./ExecutionVault.t.sol";

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract StakingVaultTest is Test {
    MockUsdc internal usdc;
    StakingVault internal vault;
    address internal admin = address(0xA11CE);
    address internal treasury = address(0xBABE);
    address internal agent = address(0xBEEF);

    function setUp() public {
        usdc = new MockUsdc();
        vault = new StakingVault(IERC20(address(usdc)), treasury, admin);
        usdc.mint(agent, 1_000e6);
    }

    function test_StakeUnstakeSlash() public {
        vm.startPrank(agent);
        usdc.approve(address(vault), 500e6);
        vault.stake(500e6);
        vm.stopPrank();
        assertEq(vault.balanceOf(agent), 500e6);

        vm.prank(agent);
        vault.unstake(200e6);
        assertEq(vault.balanceOf(agent), 300e6);

        vm.prank(admin);
        vault.slash(agent, 100e6, "constitutional_breach");
        assertEq(vault.balanceOf(agent), 200e6);
        assertEq(usdc.balanceOf(treasury), 100e6);
    }
}
'''

FILES["StrategyLifecycle.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {StrategyLifecycle} from "../src/StrategyLifecycle.sol";

contract StrategyLifecycleTest is Test {
    StrategyLifecycle internal lifecycle;
    address internal admin = address(0xA11CE);

    function setUp() public {
        lifecycle = new StrategyLifecycle(admin);
    }

    function test_DraftToLive() public {
        bytes32 strategyId = keccak256("momentum-v1");
        vm.startPrank(admin);
        lifecycle.register(strategyId, "momentum-v1");
        lifecycle.transition(strategyId, lifecycle.REGISTERED());
        lifecycle.transition(strategyId, lifecycle.PAPER());
        lifecycle.transition(strategyId, lifecycle.LIVE());
        vm.stopPrank();
        assertEq(lifecycle.state(strategyId), lifecycle.LIVE());
    }

    function test_InvalidTransitionReverts() public {
        bytes32 strategyId = keccak256("strat");
        vm.startPrank(admin);
        lifecycle.register(strategyId, "strat");
        vm.expectRevert(StrategyLifecycle.InvalidTransition.selector);
        lifecycle.transition(strategyId, lifecycle.LIVE());
        vm.stopPrank();
    }

    function test_TerminateFromAnyState() public {
        bytes32 strategyId = keccak256("strat");
        vm.startPrank(admin);
        lifecycle.register(strategyId, "strat");
        lifecycle.terminate(strategyId, "operator kill");
        vm.stopPrank();
        assertEq(lifecycle.state(strategyId), lifecycle.TERMINATED());
    }
}
'''

FILES["TradeProof.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {TradeProof} from "../src/TradeProof.sol";

contract TradeProofTest is Test {
    TradeProof internal proof;
    address internal admin = address(0xA11CE);

    function setUp() public {
        proof = new TradeProof(admin);
    }

    function test_RecordRoundTrip() public {
        bytes32 tid = keccak256("trade-1");
        bytes32 thid = keccak256("thesis-1");

        vm.prank(admin);
        proof.record(tid, thid, "0xmarket", 0, 300e6, 400_000);

        (
            bytes32 thesisId,
            string memory marketId,
            uint8 direction,
            uint256 sizeUsdc,
            uint256 entryPriceE6,
            uint64 at
        ) = proof.get(tid);
        assertEq(thesisId, thid);
        assertEq(marketId, "0xmarket");
        assertEq(direction, 0);
        assertEq(sizeUsdc, 300e6);
        assertEq(entryPriceE6, 400_000);
        assertGt(at, 0);
    }
}
'''

FILES["ZeusMultisig.t.sol"] = '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {ZeusMultisig} from "../src/governance/ZeusMultisig.sol";

contract _Target {
    uint256 public value;

    function set(uint256 v) external {
        value = v;
    }
}

contract ZeusMultisigTest is Test {
    ZeusMultisig internal multisig;
    address internal signer1 = address(0xA11CE);
    address internal signer2 = address(0xB0B);
    address internal signer3 = address(0xCAFE);
    _Target internal target;

    function setUp() public {
        address[] memory signers = new address[](3);
        signers[0] = signer1;
        signers[1] = signer2;
        signers[2] = signer3;
        multisig = new ZeusMultisig(signers, 2);
        target = new _Target();
    }

    function test_ExecutesAfterThreshold() public {
        bytes memory data = abi.encodeWithSelector(_Target.set.selector, uint256(42));

        vm.prank(signer1);
        multisig.confirm(address(target), 0, data);

        vm.prank(signer2);
        multisig.confirm(address(target), 0, data);

        multisig.execute(address(target), 0, data);
        assertEq(target.value(), 42);
    }

    function test_RejectsBelowThreshold() public {
        bytes memory data = abi.encodeWithSelector(_Target.set.selector, uint256(1));
        vm.prank(signer1);
        multisig.confirm(address(target), 0, data);

        vm.expectRevert(ZeusMultisig.InsufficientConfirmations.selector);
        multisig.execute(address(target), 0, data);
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
