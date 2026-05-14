// SPDX-License-Identifier: MIT
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
