// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20Base} from "./ERC20Base.sol";
import {Treasury} from "./Treasury.sol";

/// @notice SettlementV1 — the ledger logic wired in behind the settlement
/// proxy. It is always reached through the proxy's delegatecall, so every
/// storage access below lands in the PROXY's storage, at the slot Solidity
/// assigns here. The declaration order therefore fixes the slot numbers (see
/// soln.txt for the full proxy/V1 slot table):
///
///   slot 0  branchOperator   -- also the proxy's `admin` slot
///   slot 1  branchRegistrar   -- also the proxy's `implementation` slot
///   slot 2  branchClaimed      (this logic only)
///   slot 3  ledger             (this logic only)
///   slot 4  totalSettled       (this logic only)
///
/// branchRegistrar (slot 1) is never assigned by any function in this contract.
/// No code path here writes it. That is deliberate and structural, not an
/// oversight: it means the slot that overlaps the proxy's implementation
/// pointer has no write path through this logic at all.
contract SettlementV1 {
    address public branchOperator;              // slot 0
    address public branchRegistrar;             // slot 1  (never written here)
    mapping(address => bool) public branchClaimed; // slot 2
    mapping(address => uint256) public ledger;     // slot 3
    uint256 public totalSettled;                   // slot 4

    ERC20Base public immutable stl;
    Treasury public immutable treasury;

    constructor(ERC20Base _stl, Treasury _treasury) {
        stl = _stl;
        treasury = _treasury;
    }

    /// @notice Branch onboarding. A registrar was never wired in to gate this
    /// (branchRegistrar, slot 1, is never assigned), so onboarding is open: any
    /// node may record its operating address. A given caller may register once.
    function registerBranch(address operator) external {
        require(!branchClaimed[msg.sender], "branch: already registered");
        branchClaimed[msg.sender] = true;
        branchOperator = operator;
    }

    /// @notice Ordinary settlement deposit. Pulls `amount` STL from the caller
    /// into the treasury and credits the caller's ledger entry. (Flavor; not
    /// part of the intended path -- see soln.txt.)
    function deposit(uint256 amount) external {
        require(stl.transferFrom(msg.sender, address(treasury), amount), "deposit: transfer");
        ledger[msg.sender] += amount;
        totalSettled += amount;
    }

    /// @notice Ordinary settlement withdrawal. Debits the caller's ledger entry
    /// and releases `amount` STL back to the caller through the treasury.
    /// (Flavor; not part of the intended path -- see soln.txt.)
    function withdraw(uint256 amount) external {
        uint256 bal = ledger[msg.sender];
        require(bal >= amount, "withdraw: insufficient");
        ledger[msg.sender] = bal - amount;
        treasury.release(msg.sender, amount);
    }
}
