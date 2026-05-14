// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IExecutionVault {
    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);

    function deposit(uint256 amount) external;
    function withdraw(address to, uint256 amount) external;
    function balance() external view returns (uint256);
}
