from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, model_validator


# -------------------------
# Core Enums
# -------------------------

NodeKind = Literal[
    "service",
    "datastore",
    "queue",
    "job",
    "external",
    "client",
]

RelationKind = Literal[
    "calls",
    "publishes",
    "delivers",
    "writes",
    "reads",
    "emits",
    "ingests",
    "triggers",
]


# -------------------------
# Payload
# -------------------------

class Payload(BaseModel):
    name: Optional[str] = None
    schema_ref: Optional[str] = None
    format: Optional[Literal["json", "avro", "protobuf", "csv", "unknown"]] = None
    rate: Optional[str] = None
    delivery: Optional[
        Literal["at_most_once", "at_least_once", "exactly_once", "unknown"]
    ] = None


# -------------------------
# Node Model
# -------------------------

class Node(BaseModel):
    id: str = Field(..., description="Unique identifier in the graph")
    kind: NodeKind
    name: str

    tech: Optional[str] = None  # kafka, postgres, fastapi, etc.

    compute_model: Optional[
        Literal["request_response", "stream", "batch", "async_worker"]
    ] = None

    statefulness: Optional[Literal["stateless", "stateful"]] = None
    criticality: Optional[Literal["low", "medium", "high"]] = None

    scaling_unit: Optional[
        Literal["cpu", "partitions", "concurrency", "io", "unknown"]
    ] = None

    runtime: Optional[str] = None  # python, jvm, node, managed, etc.
    notes: Optional[str] = None


# -------------------------
# Edge Model
# -------------------------

class Edge(BaseModel):
    from_node: str = Field(..., description="Source node id")
    to_node: str = Field(..., description="Target node id")
    relation: RelationKind
    payload: Optional[Payload] = None


# -------------------------
# Graph Root
# -------------------------

class SystemGraph(BaseModel):
    schema_version: str = Field(
        default="0.1.0",
        description="Schema version for this graph (semver recommended).",
        examples=["0.1.0"],
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this graph artifact was created.",
    )

    title: Optional[str] = None
    description: Optional[str] = None

    nodes: List[Node]
    edges: List[Edge]

    @model_validator(mode="after")
    def validate_edges(self) -> "SystemGraph":
        node_ids = {n.id for n in self.nodes}

        for e in self.edges:
            if e.from_node not in node_ids:
                raise ValueError(f"Unknown from_node: {e.from_node}")
            if e.to_node not in node_ids:
                raise ValueError(f"Unknown to_node: {e.to_node}")

        return self