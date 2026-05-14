// SPDX-License-Identifier: MIT
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
