"""GraphQL schema for flexible queries.
Designed & developed by: Ali Hussein Thajil

Strawberry-based. Example queries:
  { cases(limit: 10) { caseId physics { v95 tcp } auditHash } }
  { case(id: "CASE-123") { summary auditHash } }
  { metrics { requestsProcessed uptime } }
"""
from __future__ import annotations
from typing import List, Optional

try:
    import strawberry
    from strawberry.fastapi import GraphQLRouter
    HAS_STRAWBERRY = True
except ImportError:
    HAS_STRAWBERRY = False


if HAS_STRAWBERRY:

    @strawberry.type
    class Physics:
        wepl: float = 0.0
        r80: float = 0.0
        v95: float = 0.0
        ci: float = 0.0
        hi: float = 0.0
        tcp: float = 0.0

    @strawberry.type
    class Case:
        case_id: str
        status: str = "completed"
        audit_hash: str = ""
        physics: Optional[Physics] = None
        uncertainty: float = 0.0

    @strawberry.type
    class ServerMetrics:
        requests_processed: int = 0
        cases_processed: int = 0
        uptime_s: float = 0.0
        version: str = ""

    class Query:
        @strawberry.field
        def cases(self, limit: int = 20) -> List[Case]:
            # Hook to real case store in production
            return [Case(case_id="CASE-DEMO", status="completed",
                         audit_hash="demo" * 16,
                         physics=Physics(v95=0.98, tcp=0.95))]

        @strawberry.field
        def case(self, case_id: str) -> Optional[Case]:
            return Case(case_id=case_id, status="not_found",
                        audit_hash="0" * 64)

        @strawberry.field
        def metrics(self) -> ServerMetrics:
            return ServerMetrics(version="1.0.0-pro")

    schema = strawberry.Schema(query=Query)
    graphql_router = GraphQLRouter(schema=schema, path="/graphql")
else:
    schema = None
    graphql_router = None
