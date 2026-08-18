import random
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MockPaymentAdapter:
    @staticmethod
    def initiate_payment(amount: float, method: str) -> Tuple[str, str]:
        """
        Initiates a mock payment.
        Returns: (transaction_no, status)
        """
        tx_no = f"TXN-2026-{random.randint(100000, 999999)}"
        logger.info(f"Initiated mock payment of Rs. {amount} via {method}. Tx: {tx_no}")
        return tx_no, "INITIATED"

    @staticmethod
    def process_payment_outcome(tx_no: str, outcome: str = "SUCCESS") -> Tuple[str, str]:
        """
        Simulates payment outcomes: SUCCESS, FAILED, TIMEOUT, CANCELLED
        """
        valid_outcomes = ["SUCCESS", "FAILED", "TIMEOUT", "CANCELLED"]
        status = outcome.upper() if outcome.upper() in valid_outcomes else "SUCCESS"
        
        logger.info(f"Payment transaction {tx_no} status resolved to: {status}")
        
        error_msg = None
        if status == "FAILED":
            error_msg = "Insufficient funds in mock bank account"
        elif status == "TIMEOUT":
            error_msg = "Gateway timed out"
        elif status == "CANCELLED":
            error_msg = "Transaction cancelled by citizen"
            
        return status, error_msg
