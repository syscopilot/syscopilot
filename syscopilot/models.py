from typing import List, Literal, Union

from pydantic import BaseModel, Field


class ShortReport(BaseModel):
    architecture_summary: str = Field(..., min_length=1)
    assumptions_detected: List[str]
    idempotency_risks: List[str]
    backpressure_analysis: List[str]
    failure_scenarios: List[str]
    concrete_fixes: List[str]


class Report(BaseModel):
    architecture_summary: str = Field(..., min_length=1)
    assumptions_detected: List[str]
    idempotency_risks: List[str]
    responsibility_coupling: List[str]
    backpressure_analysis: List[str]
    ingestion_vs_processing: List[str]
    failure_scenarios: List[str]
    concrete_fixes: List[str]
    suggested_metrics: List[str]
    failure_injection_tests: List[str]


Mode = Literal["short", "full"]
ReportLike = Union[ShortReport, Report]
