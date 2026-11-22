// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20Base} from "./ERC20Base.sol";
import {SettlementToken} from "./SettlementToken.sol";
import {Treasury} from "./Treasury.sol";
import {Ops} from "./Ops.sol";
import {SettlementV1} from "./SettlementV1.sol";
import {SettlementProxy} from "./SettlementProxy.sol";

/// @notice Setup — deploys and wires one fresh, fully self-contained instance of
/// the settlement node, funds the player, and exposes isSolved().
///
/// Win condition: the treasury's STL reserve ends below 1% of its starting
/// balance. Everything below is constructed fresh per instance; there is no
/// shared state and no cross-instance assumption.
contract Setup {
    // ----- fixed instance parameters -----
    uint256 public constant TREASURY_STL = 5_000_000 ether;
    uint256 public constant PLAYER_STL = 200 ether; // flavor only -- not needed to solve

    // ----- deployed system -----
    address public immutable player;
    SettlementToken public immutable stl;
    Ops public immutable ops;
    Treasury public immutable treasury;
    SettlementV1 public immutable settlementV1;
    SettlementProxy public immutable proxy;

    constructor(address _player) {
        require(_player != address(0), "setup: zero player");
        player = _player;

        // Full supply minted to this Setup, then distributed below.
        stl = new SettlementToken(TREASURY_STL + PLAYER_STL);

        // Initial, legitimate, player-inaccessible admin of the proxy.
        ops = new Ops();

        // Treasury needs its settlement system named at construction, but the
        // proxy does not exist yet. Resolve the ordering with a one-time wire():
        // deploy the treasury now, name the proxy once both sides exist.
        treasury = new Treasury(ERC20Base(address(stl)));

        settlementV1 = new SettlementV1(ERC20Base(address(stl)), treasury);

        proxy = new SettlementProxy(address(ops), address(settlementV1));

        // One-time wiring: the proxy is the treasury's sole authorised caller.
        treasury.wire(address(proxy));

        // Fund the treasury reserve and hand the player a modest wallet.
        require(stl.transfer(address(treasury), TREASURY_STL), "setup: fund treasury");
        require(stl.transfer(player, PLAYER_STL), "setup: fund player");
    }

    /// @notice Win check: the treasury reserve has been moved out below 1% of
    /// its starting balance.
    function isSolved() external view returns (bool) {
        return stl.balanceOf(address(treasury)) < (TREASURY_STL / 100);
    }
}
