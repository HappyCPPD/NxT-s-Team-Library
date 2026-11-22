// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20Base} from "./ERC20Base.sol";

/// @notice Treasury — custodies the settlement node's STL reserve. The only way
/// STL leaves the treasury is a `release` by the single wired settlement system
/// (the proxy). There is no owner withdrawal path; once wired, the settlement
/// system is the sole caller that `release` accepts.
contract Treasury {
    ERC20Base public immutable stl;
    address public immutable admin;
    address public settlementSystem;

    constructor(ERC20Base _stl) {
        stl = _stl;
        admin = msg.sender;
    }

    /// @notice One-time wiring: name the settlement system allowed to draw.
    /// Callable once, by the deployer (Setup) only, then locked. This mirrors a
    /// vault naming its sole authorised spender after both sides exist.
    function wire(address system) external {
        require(msg.sender == admin, "treasury: not admin");
        require(settlementSystem == address(0), "treasury: wired");
        require(system != address(0), "treasury: zero system");
        settlementSystem = system;
    }

    /// @notice Release STL to a recipient. Only the wired settlement system may
    /// call. `msg.sender` here is whatever called Treasury directly; a call made
    /// from code running via the settlement system's delegatecall appears to
    /// come from the settlement system's own address.
    function release(address to, uint256 amount) external {
        require(msg.sender == settlementSystem, "treasury: not system");
        require(stl.transfer(to, amount), "treasury: transfer");
    }

    function reserveBalance() external view returns (uint256) {
        return stl.balanceOf(address(this));
    }
}
