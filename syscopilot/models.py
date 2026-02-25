from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ShortReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architecture_summary: str = Field(..., min_length=1)
    assumptions_detected: List[str]
    idempotency_risks: List[str]
    backpressure_analysis: List[str]
    failure_scenarios: List[str]
    concrete_fixes: List[str]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class SystemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    domain: Optional[str] = None
    goals: List[str]
    non_goals: List[str]


class ComponentRuntime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    platform: Optional[str] = None


class ComponentScaling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: Optional[int] = None
    max: Optional[int] = None
    strategy: Optional[str] = None


class Component(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    type: str
    name: str
    responsibilities: List[str]
    depends_on: List[str]
    runtime: Optional[ComponentRuntime] = None
    scaling: Optional[ComponentScaling] = None


class LinkTransport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    name: str
    format: Optional[str] = None


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    from_id: str = Field(..., min_length=1)
    to_id: str = Field(..., min_length=1)
    transport: LinkTransport
    semantics: List[str]
    delivery: Optional[str] = None
    ordering: Optional[str] = None
    key: Optional[str] = None
    backpressure: Optional[str] = None


class DataStore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    type: str
    ownership: str
    notes: List[str]
    retention: Optional[str] = None


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    name: str
    owner_component_id: str = Field(..., min_length=1)
    schema: dict[str, Any]
    evolution: Optional[str] = None


class Deploy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orchestration: Optional[str] = None
    regions: List[str]
    observability: List[str]
    notes: List[str]


class Requirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slos: List[str]
    constraints: List[str]
    throughput_targets: List[str]
    latency_budgets: List[str]


class SystemSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["syscopilot.systemspec.v1"]
    system: SystemInfo
    components: List[Component]
    links: List[Link]
    data_stores: List[DataStore]
    contracts: List[Contract]
    deploy: Deploy
    requirements: Requirements
    open_questions: List[str]
    extensions: dict[str, Any] = Field(default_factory=dict)


Mode = Literal["short", "full"]
ReportLike = Union[ShortReport, Report]
