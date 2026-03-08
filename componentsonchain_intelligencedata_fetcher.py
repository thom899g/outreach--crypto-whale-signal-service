"""
Robust blockchain data fetcher with error handling and rate limiting
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from web3 import Web3, HTTPProvider
from web3.exceptions import BlockNotFound, TransactionNotFound
from web3.middleware import geth_poa_middleware
import pandas as pd

from config.settings import config, BlockchainNetwork
from utils.logger import get_logger, log_operation

logger = get_logger()

@dataclass
class WalletData:
    """Data container for wallet information"""
    address: str
    transactions: List[Dict]
    token_balances: Dict[str, float]
    last_activity: datetime
    total_volume_eth: float
    interaction_count: int

class BlockchainDataFetcher:
    """Robust blockchain data fetcher with comprehensive error handling"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.ETHEREUM_MAINNET):
        self.network_config = config.get_network_config(network)
        self.web3 = self._initialize_web3()
        self.rate_limit_delay = 0.1  # Seconds between requests
        self.last_request_time = 0
        
    def _initialize_web3(self) -> Web3:
        """Initialize Web3 connection with error handling"""
        try:
            w3 = Web3(HTTPProvider(self.network_config.rpc_url))
            
            # Add POA middleware for networks like BSC
            if self.network_config.network in [BlockchainNetwork.BSC_MAINNET]:
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Test connection
            if not w3.is_connected():
                raise ConnectionError(f"Failed to connect to {self.network_config.network.value}")
            
            logger.info(f"Connected to {self.network_config.network.value} at block {w3.eth.block_number}")
            return w3
            
        except Exception as e:
            logger.error(f"Failed to initialize Web3: {str(e)}")
            raise
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    @log_operation("fetch_wallet_transactions")
    def fetch_wallet_transactions(self, wallet_address: str, days: int = 90) -> List[Dict]:
        """
        Fetch transactions for a wallet address with comprehensive error handling
        
        Args:
            wallet_address: Ethereum wallet address
            days: Number of days of history to fetch
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Validate address
            if not self.web3.is_address(wallet_address):
                raise ValueError(f"Invalid Ethereum address: {wallet_address}")
            
            checksum_address = self.web3.to_checksum_address(wallet_address)
            current_block = self.web3.eth.block_number
            
            # Calculate block range (approximate blocks per day: 7200 for Ethereum)
            blocks_per_day = 7200
            from_block = max(0, current_block - (days * blocks_per_day))
            
            transactions = []
            max_blocks_per_request = 10000
            
            # Fetch transactions in chunks to avoid timeout
            for start_block in range(from_block, current_block, max_blocks_per_request):
                self._enforce_rate_limit()
                
                end_block = min(start_block + max_blocks_per_request - 1, current_block)
                
                try:
                    # Fetch transactions from the wallet
                    txs = self.web3.eth.get_transactions_by_address(
                        checksum_address,
                        from_block=start_block,
                        to_block=end_block
                    )
                    transactions.extend(txs)
                    
                    logger.debug(f"Fetched {len(txs)} transactions from blocks {start_block}-{end_block}")
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch transactions for blocks {start_block}-{end_block}: {str(e)}")
                    continue
            
            # Parse transaction data
            parsed_transactions = []
            for tx_hash in transactions:
                try:
                    self._enforce_rate_limit()
                    tx = self.web3.eth.get_transaction(tx_hash)
                    tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                    
                    parsed_tx = {
                        'hash': tx_hash.hex(),
                        'from': tx['from'],
                        'to': tx['to'],
                        'value': self.web3.from_wei(tx['value'], 'ether'),
                        'gas_used': tx_receipt['gasUsed'] if tx_receipt else None,
                        'gas_price': self.web3.from_wei(tx['gasPrice'], 'gwei'),
                        'block_number': tx['blockNumber'],
                        'timestamp': self._get_block_timestamp(tx['blockNumber']),
                        'input': tx['input'][:100] if tx['input'] else '',  # First 100 chars
                        'is_contract_creation': tx['to'] is None
                    }
                    parsed_transactions.append(parsed_tx)
                    
                except (TransactionNotFound, BlockNotFound) as e:
                    logger.debug(f"Transaction not found or block missing: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to parse transaction {tx_hash.hex()}: {str(e)}")
                    continue
            
            logger.info(f"Successfully fetched {len(parsed_transactions)} transactions for {wallet_address}")
            return parsed_transactions
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions for {wallet_address}: {str