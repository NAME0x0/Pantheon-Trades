// SPDX-License-Identifier: MIT
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
