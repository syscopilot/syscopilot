from typing import List, Optional, Literal
from pydantic import BaseModel, Field


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

    # Optional classification
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

from pydantic import model_validator


class SystemGraph(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

    @model_validator(mode="after")
    def validate_edges(self):
        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.from_node not in node_ids:
                raise ValueError(f"Unknown from_node: {edge.from_node}")
            if edge.to_node not in node_ids:
                raise ValueError(f"Unknown to_node: {edge.to_node}")
        return self