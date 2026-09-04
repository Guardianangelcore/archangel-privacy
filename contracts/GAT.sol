// SPDX-License-Identifier: UNLICENSED
// Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
pragma solidity ^0.8.24;

/// @title GA-T — Guardian Angel Token (Base L2, ERC-20)
/// @notice Fixed cap of 1,000,000,000 GA-T (18 decimals). 25 % genesis mint to the Founder wallet,
///         the remaining 75 % is mintable ONLY by the Foundation backend (MINTER) as users earn
///         in-app GA-T through verified subscription purchases and peer-confirmed help.
///         Deployed with the Founder wallet as owner: 0x0E6693153961c01CEa3e73e4e9596aCF35315567
contract GAT {
    string public constant name = "Guardian Angel Token";
    string public constant symbol = "GA-T";
    uint8 public constant decimals = 18;
    uint256 public constant CAP = 1_000_000_000 * 1e18;
    uint256 public constant GENESIS_FOUNDER_BPS = 2_500;   // 25 %

    uint256 public totalSupply;
    address public owner;
    mapping(address => bool) public isMinter;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    // In-app ledger tx ids already minted (idempotency for the backend mint queue)
    mapping(bytes32 => bool) public mintedLedgerTx;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event MinterUpdated(address indexed minter, bool allowed);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event LedgerMint(bytes32 indexed ledgerTx, address indexed to, uint256 value);

    modifier onlyOwner() { require(msg.sender == owner, "GAT: not owner"); _; }
    modifier onlyMinter() { require(isMinter[msg.sender] || msg.sender == owner, "GAT: not minter"); _; }

    constructor(address founder, address minter) {
        require(founder != address(0), "GAT: founder=0");
        owner = founder;
        emit OwnershipTransferred(address(0), founder);
        if (minter != address(0)) { isMinter[minter] = true; emit MinterUpdated(minter, true); }
        uint256 genesis = CAP * GENESIS_FOUNDER_BPS / 10_000;
        _mint(founder, genesis);
    }

    // ---- ERC-20 ----
    function transfer(address to, uint256 value) external returns (bool) { _transfer(msg.sender, to, value); return true; }
    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value; emit Approval(msg.sender, spender, value); return true;
    }
    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 a = allowance[from][msg.sender];
        require(a >= value, "GAT: allowance");
        if (a != type(uint256).max) allowance[from][msg.sender] = a - value;
        _transfer(from, to, value); return true;
    }

    // ---- Foundation controls ----
    function setMinter(address minter, bool allowed) external onlyOwner { isMinter[minter] = allowed; emit MinterUpdated(minter, allowed); }
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "GAT: owner=0"); emit OwnershipTransferred(owner, newOwner); owner = newOwner;
    }

    /// @notice Backend bridge: mints in-app earned GA-T on-chain, once per ledger tx id.
    function mintFromLedger(address to, uint256 value, bytes32 ledgerTx) external onlyMinter {
        require(!mintedLedgerTx[ledgerTx], "GAT: already minted");
        mintedLedgerTx[ledgerTx] = true;
        _mint(to, value);
        emit LedgerMint(ledgerTx, to, value);
    }

    function burn(uint256 value) external { _burn(msg.sender, value); }

    // ---- internals ----
    function _mint(address to, uint256 value) internal {
        require(to != address(0), "GAT: to=0");
        require(totalSupply + value <= CAP, "GAT: cap exceeded");
        totalSupply += value; balanceOf[to] += value; emit Transfer(address(0), to, value);
    }
    function _burn(address from, uint256 value) internal {
        require(balanceOf[from] >= value, "GAT: balance"); balanceOf[from] -= value; totalSupply -= value; emit Transfer(from, address(0), value);
    }
    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0), "GAT: to=0"); require(balanceOf[from] >= value, "GAT: balance");
        balanceOf[from] -= value; balanceOf[to] += value; emit Transfer(from, to, value);
    }
}
