"""FastAPI service exposing the five 9antra agents and the purchase workflow (port 8001).

Run (from the ai-services/ folder):
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

HTTP concerns only: validation, status codes, auth. All business logic lives in agents/ and workflow/.
"""
from __future__ import annotations

import os
import secrets
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from agents import CustomerIntelAgent, FinancialAnalystAgent, FraudAgent, PaymentAgent, SalesAgent
from core.llm_client import get_default_client
from schemas.common import AgentResponse
from schemas.financial import FinancialOutput, FinancialQuery
from schemas.fraud import FraudCheckInput, FraudOutput
from schemas.intel import CustomerInsights, IntelInput
from schemas.payment import PaymentEvent, PaymentOutput
from schemas.sales import SalesInput, SalesOutput
from workflow import PurchaseWorkflow, PurchaseWorkflowRequest, PurchaseWorkflowResponse

VERSION = "1.0.0"

app = FastAPI(
    title="9antra AI Agents",
    version=VERSION,
    description="Five AI agents (sales, customer intelligence, fraud, payment, financial analysis) and the "
                "complete purchase workflow. **All data and payments are SIMULATED.** "
                "Default mode is `mock` (no LLM calls).",
)


# ----------------------------------------------------------------------------- dependencies
def require_api_key(x_api_key: str | None = Header(default=None, description="required when INTERNAL_API_KEY is set")):
    """Internal auth shared with the Node.js backend. Disabled when INTERNAL_API_KEY is empty (local dev)."""
    expected = os.getenv("INTERNAL_API_KEY", "")
    if expected and not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing X-API-Key")


@lru_cache(maxsize=1)
def agents() -> dict:
    llm = get_default_client()
    return {"sales": SalesAgent(llm), "intel": CustomerIntelAgent(llm), "fraud": FraudAgent(llm),
            "payment": PaymentAgent(llm), "financial": FinancialAnalystAgent(llm), "workflow": PurchaseWorkflow(llm)}


def _respond(resp: AgentResponse) -> AgentResponse:
    if resp.status == "error":  # agent-level validation/data error -> 422 with the structured envelope
        return JSONResponse(status_code=422, content=resp.model_dump(mode="json"))  # type: ignore[return-value]
    return resp


# ----------------------------------------------------------------------------- endpoints
@app.get("/health", tags=["service"])
def health() -> dict:
    llm = get_default_client()
    return {"status": "ok", "service": "9antra-ai-agents", "version": VERSION, "mode": llm.mode,
            "provider": llm.provider, "model": llm.model, "agents": ["sales", "customer_intel", "fraud", "payment", "financial"],
            "auth_required": bool(os.getenv("INTERNAL_API_KEY")), "data": "simulated"}


@app.post("/workflow/purchase", response_model=PurchaseWorkflowResponse, tags=["workflow"],
          dependencies=[Depends(require_api_key)],
          responses={404: {"description": "unknown course (structured workflow response)"},
                     422: {"description": "invalid request"}, 401: {"description": "bad API key"}})
def purchase_workflow(req: PurchaseWorkflowRequest):
    """Complete journey: Sales -> Customer Intelligence -> Order -> Fraud -> Payment -> Financial Analyst.

    Always returns the full structured result. HTTP 200 for every business outcome (completed, failed,
    pending, blocked, awaiting approval, no purchase); HTTP 404 when `course_id` is not in the catalog.
    """
    result = agents()["workflow"].run(req)
    if result.final_status == "unknown_course":
        return JSONResponse(status_code=404, content=result.model_dump(mode="json"))
    if result.final_status == "error":
        return JSONResponse(status_code=500, content=result.model_dump(mode="json"))
    return result


@app.post("/agents/sales", response_model=AgentResponse[SalesOutput], tags=["agents"],
          dependencies=[Depends(require_api_key)])
def sales_agent(body: SalesInput):
    return _respond(agents()["sales"].run(body))


@app.post("/agents/customer-intelligence", response_model=AgentResponse[CustomerInsights], tags=["agents"],
          dependencies=[Depends(require_api_key)])
def customer_intel_agent(body: IntelInput):
    return _respond(agents()["intel"].run(body))


@app.post("/agents/fraud", response_model=AgentResponse[FraudOutput], tags=["agents"],
          dependencies=[Depends(require_api_key)])
def fraud_agent(body: FraudCheckInput):
    return _respond(agents()["fraud"].run(body))


@app.post("/agents/payment", response_model=AgentResponse[PaymentOutput], tags=["agents"],
          dependencies=[Depends(require_api_key)])
def payment_agent(body: PaymentEvent):
    return _respond(agents()["payment"].run(body))


@app.post("/agents/financial", response_model=AgentResponse[FinancialOutput], tags=["agents"],
          dependencies=[Depends(require_api_key)])
def financial_agent(body: FinancialQuery):
    return _respond(agents()["financial"].run(body))
