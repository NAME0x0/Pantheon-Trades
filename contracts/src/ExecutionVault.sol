// SPDX-License-Identifier: MIT
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
