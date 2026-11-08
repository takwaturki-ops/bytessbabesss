"""The five 9antra agents. Each exposes `agent.run(input_data) -> AgentResponse` (validated)."""
from agents.customer_intel_agent import CustomerIntelAgent
from agents.financial_agent import FinancialAnalystAgent
from agents.fraud_agent import FraudAgent
from agents.payment_agent import PaymentAgent
from agents.sales_agent import SalesAgent

AGENTS = {
    "sales": SalesAgent,
    "customer_intel": CustomerIntelAgent,
    "payment": PaymentAgent,
    "financial": FinancialAnalystAgent,
    "fraud": FraudAgent,
}

__all__ = ["AGENTS", "SalesAgent", "CustomerIntelAgent", "PaymentAgent", "FinancialAnalystAgent", "FraudAgent"]
