"""
Centralized configuration management with environment validation
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BlockchainNetwork(Enum):
    """Supported blockchain networks"""
    ETHEREUM_MAINNET = "mainnet"
    ETHEREUM_SEPOLIA = "sepolia"
    BSC_MAINNET = "bsc"
    ARBITRUM_ONE = "arbitrum"

@dataclass
class BlockchainConfig:
    """Blockchain configuration"""
    network: BlockchainNetwork
    rpc_url: str
    chain_id: int
    explorer_url: str
    native_token: str

@dataclass
class HeuristicConfig:
    """Configuration for clustering heuristics"""
    min_wallet_balance_eth: float = 10.0
    days_of_data: int = 90
    min_tx_count: int = 50
    max_clusters: int = 100
    dbscan_eps: float = 0.5
    dbscan_min_samples: int = 5

@dataclass
class FirebaseConfig:
    """Firebase configuration"""
    project_id: str
    private_key: str
    client_email: str
    database_url: Optional[str] = None

class Config:
    """Main configuration class"""
    
    def __init__(self):
        # Blockchain configurations
        self.blockchains: Dict[BlockchainNetwork, BlockchainConfig] = {
            BlockchainNetwork.ETHEREUM_MAINNET: BlockchainConfig(
                network=BlockchainNetwork.ETHEREUM_MAINNET,
                rpc_url=f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}",
                chain_id=1,
                explorer_url="https://api.etherscan.io/api",
                native_token="ETH"
            ),
            BlockchainNetwork.ETHEREUM_SEPOLIA: BlockchainConfig(
                network=BlockchainNetwork.ETHEREUM_SEPOLIA,
                rpc_url=f"https://sepolia.infura.io/v3/{os.getenv('INFURA_API_KEY')}",
                chain_id=11155111,
                explorer_url="https://api-sepolia.etherscan.io/api",
                native_token="ETH"
            )
        }
        
        # Heuristic configuration
        self.heuristics = HeuristicConfig(
            min_wallet_balance_eth=float(os.getenv('MIN_WALLET_BALANCE_ETH', 10.0)),
            days_of_data=int(os.getenv('DAYS_OF_DATA', 90)),
            min_tx_count=int(os.getenv('MIN_TX_COUNT', 50)),
            max_clusters=int(os.getenv('MAX_CLUSTERS', 100)),
            dbscan_eps=0.5,
            dbscan_min_samples=5
        )
        
        # Firebase configuration
        self.firebase = FirebaseConfig(
            project_id=os.getenv('FIREBASE_PROJECT_ID', ''),
            private_key=os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            client_email=os.getenv('FIREBASE_CLIENT_EMAIL', '')
        )
        
        # Operational limits
        self.max_wallets_per_run = int(os.getenv('MAX_WALLETS_PER_RUN', 1000))
        
        # Validate configuration
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration and raise errors for missing required values"""
        errors = []
        
        # Check API keys
        if not os.getenv('INFURA_API_KEY'):
            errors.append("INFURA_API_KEY is required")
        
        if not os.getenv('ALCHEMY_API_KEY'):
            logging.warning("ALCHEMY_API_KEY not set, some features may be limited")
        
        # Check Firebase configuration
        if not all([self.firebase.project_id, self.firebase.private_key, self.firebase.client_email]):
            errors.append("Firebase configuration incomplete")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        logging.info("Configuration validated successfully")
    
    def get_network_config(self, network: BlockchainNetwork) -> BlockchainConfig:
        """Get configuration for specific network"""
        if network not in self.blockchains:
            raise ValueError(f"Unsupported network: {network}")
        return self.blockchains[network]

# Global configuration instance
config = Config()