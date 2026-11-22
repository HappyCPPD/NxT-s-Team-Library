// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20Base} from "./ERC20Base.sol";

/// @notice STL — the unit the settlement node holds in reserve. The full supply
/// is minted once, to the deployer (Setup), at construction.
contract SettlementToken is ERC20Base {
    constructor(uint256 initialSupply) ERC20Base("Settlement Unit", "STL") {
        _mint(msg.sender, initialSupply);
    }
}
