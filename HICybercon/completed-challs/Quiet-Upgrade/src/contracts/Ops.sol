// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Ops — the settlement node's operations account. It is the proxy's
/// initial, legitimate admin at deploy time. It has no externally reachable
/// state-changing function, no fallback, and no payable receive that does
/// anything: nothing anyone calls on it causes it to act. Its only purpose is
/// to be a real, nonzero, player-inaccessible admin address, so that obtaining
/// the proxy's admin role is actually required rather than trivially available.
contract Ops {
    address public immutable deployer;

    constructor() {
        deployer = msg.sender;
    }

    function identify() external view returns (address) {
        return deployer;
    }
}
