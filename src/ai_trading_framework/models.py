from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class Action(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RiskDecision(StrEnum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    REJECTED = "REJECTED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"


class AuthMode(StrEnum):
    DISABLED = "DISABLED"
    PASSWORD = "PASSWORD"
    OIDC = "OIDC"
    HYBRID = "HYBRID"


class OperatorRole(StrEnum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class EventType(StrEnum):
    MARKET_CONTEXT_BUILT = "MarketContextBuilt"
    FEATURES_COMPUTED = "FeaturesComputed"
    SIGNAL_GENERATED = "SignalGenerated"
    RECOMMENDATION_CREATED = "RecommendationCreated"
    EXPLANATION_GENERATED = "ExplanationGenerated"
    RISK_EVALUATED = "RiskEvaluated"
    APPROVAL_REQUESTED = "ApprovalRequested"
    APPROVAL_GRANTED = "ApprovalGranted"
    APPROVAL_REJECTED = "ApprovalRejected"
    EXECUTION_REQUESTED = "ExecutionRequested"
    EXECUTION_COMPLETED = "ExecutionCompleted"
    EXECUTION_FAILED = "ExecutionFailed"


class BrokerName(StrEnum):
    PAPER = "PAPER"
    ZERODHA = "ZERODHA"
    GROWW = "GROWW"


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"
    MUTUAL_FUND = "MUTUAL_FUND"
    INDEX = "INDEX"
    BOND = "BOND"
    UNKNOWN = "UNKNOWN"


class BrokerProduct(StrEnum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"
    MTF = "MTF"
    COIN = "COIN"
    DELIVERY = "DELIVERY"


class OrderVariety(StrEnum):
    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    BO = "bo"
    ICEBERG = "iceberg"
    AUCTION = "auction"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class BrokerCapabilities(BaseModel):
    supports_market_orders: bool = True
    supports_limit_orders: bool = True
    supports_stop_loss: bool = True
    supports_positions: bool = True
    supports_holdings: bool = True
    supports_instruments_master: bool = False
    supports_intraday: bool = False
    supports_websocket: bool = False
    supports_options: bool = False
    supports_equities: bool = True
    supports_etfs: bool = False
    supports_futures: bool = False
    supports_commodities: bool = False
    supports_currency: bool = False
    supports_mutual_funds: bool = False


class InstrumentDescriptor(BaseModel):
    broker: BrokerName | None = None
    symbol: str
    tradingsymbol: str | None = None
    name: str | None = None
    exchange: str | None = None
    segment: str | None = None
    asset_class: AssetClass = AssetClass.UNKNOWN
    instrument_type: str | None = None
    instrument_token: str | None = None
    exchange_token: str | None = None
    isin: str | None = None
    expiry: date | None = None
    strike: float | None = None
    lot_size: int | None = None
    tick_size: float | None = None
    minimum_purchase_amount: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(BaseModel):
    supports_intraday: bool = False
    supports_news: bool = False
    supports_fundamentals: bool = False
    supports_sentiment: bool = False
    supports_streaming: bool = False


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceSnapshot(BaseModel):
    symbol: str
    price: float
    change_percent: float = 0.0
    volume: int = 0
    as_of: datetime = Field(default_factory=utcnow)


class NewsArticle(BaseModel):
    article_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    headline: str
    summary: str
    sentiment_score: float = 0.0
    published_at: datetime = Field(default_factory=utcnow)


class FundamentalSnapshot(BaseModel):
    symbol: str
    sector: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    revenue_growth_percent: float | None = None
    summary: str | None = None


class SentimentSnapshot(BaseModel):
    symbol: str
    score: float
    label: str
    summary: str


class Position(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    unrealized_pnl: float = 0.0
    broker_account_id: str | None = None
    asset_class: AssetClass = AssetClass.UNKNOWN
    product: str | None = None
    instrument: InstrumentDescriptor | None = None


class PortfolioState(BaseModel):
    cash_available: float = 1_000_000.0
    positions: list[Position] = Field(default_factory=list)
    realized_pnl: float = 0.0
    daily_pnl: float = 0.0


class MarketContext(BaseModel):
    symbol: str
    instrument: InstrumentDescriptor | None = None
    horizon: str = "swing"
    lookback_days: int = 60
    price: PriceSnapshot
    candles: list[Candle] = Field(default_factory=list)
    fundamentals: FundamentalSnapshot | None = None
    news: list[NewsArticle] = Field(default_factory=list)
    sentiment: SentimentSnapshot | None = None
    portfolio_state: PortfolioState = Field(default_factory=PortfolioState)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureBundle(BaseModel):
    symbol: str
    features: dict[str, float | str | int] = Field(default_factory=dict)


class Signal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    instrument: InstrumentDescriptor | None = None
    strategy_name: str
    action: Action
    confidence: float
    rationale: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluatedSignal(BaseModel):
    signal_id: str
    symbol: str
    instrument: InstrumentDescriptor | None = None
    action: Action
    confidence: float
    score: float
    factors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationExplanation(BaseModel):
    why_this_trade: str = ""
    signals_used: list[str] = Field(default_factory=list)
    risk_checks: list[str] = Field(default_factory=list)
    ai_reasoning: str = ""
    execution_constraints: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str | None = None
    symbol: str
    instrument: InstrumentDescriptor | None = None
    action: Action
    confidence: float
    thesis: str
    strategy_name: str
    supporting_evidence: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    signal: EvaluatedSignal | None = None
    explanation: RecommendationExplanation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def explain(self) -> RecommendationExplanation:
        return self.explanation or RecommendationExplanation()


class RiskCheckResult(BaseModel):
    policy_name: str
    decision: RiskDecision
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskEvaluation(BaseModel):
    decision: RiskDecision
    summary: str
    checks: list[RiskCheckResult] = Field(default_factory=list)
    max_position_size: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    recommendation_id: str
    run_id: str
    broker: BrokerName
    status: ApprovalStatus = ApprovalStatus.PENDING
    token: str = Field(default_factory=lambda: str(uuid4()))
    requested_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    consumed_at: datetime | None = None


class OperatorIdentity(BaseModel):
    operator_id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    display_name: str
    role: OperatorRole = OperatorRole.ADMIN
    auth_provider: str = "password"
    provider_subject: str | None = None
    password_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    last_login_at: datetime | None = None


class OperatorSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    operator_id: str
    session_token: str
    auth_provider: str
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class OAuthState(BaseModel):
    state_id: str = Field(default_factory=lambda: str(uuid4()))
    provider_name: str
    state_token: str
    code_verifier: str
    redirect_after: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime


class BrokerAuthSession(BaseModel):
    broker: BrokerName
    access_token: str
    refresh_token: str | None = None
    public_token: str | None = None
    request_token: str | None = None
    api_key: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    email: str | None = None
    login_time: str | None = None
    actor_operator_id: str | None = None
    received_at: datetime = Field(default_factory=utcnow)
    raw: dict[str, Any] = Field(default_factory=dict)


class OrderRequest(BaseModel):
    recommendation_id: str
    approval_token: str | None = None
    symbol: str
    instrument: InstrumentDescriptor | None = None
    broker: BrokerName = BrokerName.PAPER
    action: Action
    quantity: float
    order_type: OrderType = OrderType.MARKET
    product: BrokerProduct = BrokerProduct.CNC
    variety: OrderVariety = OrderVariety.REGULAR
    limit_price: float | None = None
    stop_price: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderPreview(BaseModel):
    recommendation_id: str
    broker: BrokerName
    action: Action
    symbol: str
    instrument: InstrumentDescriptor | None = None
    quantity: float
    order_type: OrderType
    estimated_notional: float
    warnings: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    recommendation_id: str
    broker: BrokerName
    status: str
    message: str
    fill_price: float | None = None
    filled_quantity: float | None = None
    broker_order_id: str | None = None
    executed_at: datetime = Field(default_factory=utcnow)


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    run_id: str
    created_at: datetime = Field(default_factory=utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=utcnow)
    symbol: str
    events: list[Event] = Field(default_factory=list)


class StrategyBenchmark(BaseModel):
    strategy_name: str
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    approval_rate: float
    execution_slippage_bps: float


class InvestmentCandidate(BaseModel):
    symbol: str
    recommendation_id: str
    action: Action
    confidence: float
    score: float
    estimated_entry_price: float
    estimated_notional: float
    suggested_quantity: float
    risk_decision: RiskDecision
    thesis: str
    asset_class: AssetClass = AssetClass.UNKNOWN


class InvestmentPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    broker: BrokerName
    budget: float
    symbols_considered: list[str] = Field(default_factory=list)
    selected: InvestmentCandidate | None = None
    alternatives: list[InvestmentCandidate] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    approval: ApprovalRequest | None = None
    summary: str = ""
    next_step: str = ""
