// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice SettlementProxy — a minimal delegatecall proxy for the settlement
/// logic. It is written the naive way on purpose: its two pointers live in the
/// first two sequential storage slots rather than in hashed, pseudo-random
/// EIP-1967-style slots. A proxy that hashes its slots into out-of-the-way
/// locations avoids overlapping the logic contract's own variables; this one
/// does not bother.
///
///   slot 0  admin
///   slot 1  implementation
///
/// The upgrade path (`upgradeTo`) was added in a later release and was never
/// checked against the logic contract's existing storage layout.
contract SettlementProxy {
    address public admin;          // slot 0
    address public implementation; // slot 1

    bytes32 constant QU_TAG = keccak256("quiet-upgrade.proxiable");

    constructor(address _admin, address _implementation) {
        admin = _admin;
        implementation = _implementation;
    }

    function changeAdmin(address newAdmin) external {
        require(msg.sender == admin, "not admin");
        admin = newAdmin;
    }

    /// @notice Install a new logic contract. Only the admin may call, and the
    /// candidate must prove it was built for THIS proxy by returning, from
    /// `proxiableSlot()`, keccak256(abi.encodePacked(QU_TAG, address(this))).
    /// `address(this)` is evaluated in the proxy's own execution context (this
    /// function is not delegated), so the expected value is bound to this
    /// specific proxy instance -- a value computed for a different proxy will
    /// not match.
    function upgradeTo(address newImpl) external {
        require(msg.sender == admin, "not admin");
        require(newImpl.code.length > 0, "not a contract");
        bytes32 expected = keccak256(abi.encodePacked(QU_TAG, address(this)));
        (bool ok, bytes memory ret) = newImpl.staticcall(
            abi.encodeWithSignature("proxiableSlot()")
        );
        require(ok && ret.length == 32, "candidate rejected");
        require(abi.decode(ret, (bytes32)) == expected, "candidate rejected");
        implementation = newImpl;
    }

    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}
}
