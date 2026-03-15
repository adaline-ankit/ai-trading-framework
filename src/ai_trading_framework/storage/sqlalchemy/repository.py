from __future__ import annotations

import json

from sqlalchemy import String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_trading_framework.models import RunRecord


class Base(DeclarativeBase):
    pass


class RunModel(Base):
    __tablename__ = "framework_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class SQLAlchemyRunStore:
    def __init__(self, database_url: str = "sqlite:///./ai_trading_framework.db") -> None:
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)

    def save(self, run: RunRecord) -> None:
        payload = json.dumps(run.model_dump(mode="json"))
        with Session(self.engine) as session:
            session.merge(RunModel(run_id=run.run_id, symbol=run.symbol, payload=payload))
            session.commit()

    def get(self, run_id: str) -> RunRecord | None:
        with Session(self.engine) as session:
            model = session.scalar(select(RunModel).where(RunModel.run_id == run_id))
            if not model:
                return None
            return RunRecord.model_validate(json.loads(model.payload))

    def list_runs(self, limit: int = 100) -> list[RunRecord]:
        with Session(self.engine) as session:
            models = session.scalars(select(RunModel).limit(limit)).all()
            return [RunRecord.model_validate(json.loads(model.payload)) for model in models]
