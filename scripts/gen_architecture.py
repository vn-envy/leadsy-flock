# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

"""Judge-facing architecture. Regenerates docs/architecture.png via mingrammer/diagrams."""

from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.analytics import PubSub
from diagrams.gcp.compute import Run
from diagrams.gcp.database import Firestore
from diagrams.gcp.devtools import SDK, ServiceCatalog
from diagrams.gcp.ml import AIPlatform, VertexAI
from diagrams.gcp.network import Armor
from diagrams.gcp.operations import Monitoring
from diagrams.gcp.storage import GCS
from diagrams.onprem.client import Users

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture"

GRAPH = {
    "bgcolor": "#f7f5f0",
    "pad": "0.7",
    "splines": "spline",
    "nodesep": "0.7",
    "ranksep": "1.0",
    "fontname": "Helvetica",
    "fontsize": "20",
    "fontcolor": "#3a3d40",
}
NODE = {
    "fontname": "Helvetica",
    "fontsize": "12",
    "fontcolor": "#3a3d40",
}
CLUSTER = {
    "fontname": "Helvetica",
    "fontsize": "13",
    "fontcolor": "#5b6440",
    "bgcolor": "#faf8f4",
    "pencolor": "#ddd8d0",
}
INK = "#5b6440"
PINK = "#d49a9a"
ASH = "#8a8f93"


def main() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with Diagram(
        "Leadsy Flock  ·  Fortified Enterprise Fleet  ·  asia-south1",
        filename=str(OUT),
        show=False,
        direction="LR",
        outformat="png",
        graph_attr=GRAPH,
        node_attr=NODE,
    ):
        shop = Users("Neighbourhood shop\npastes a listing it owns")

        with Cluster("Door  ·  flock-api  ·  Cloud Run", graph_attr=CLUSTER):
            roost = Run("Roost  ·  YES\nnever autopost")
            flo = SDK("Flo  ·  Google ADK")
            gemini = VertexAI("Gemini 3.5 Flash")
            armor = Armor("Model Armor")
            card = ServiceCatalog("A2A AgentCard")

        bus = PubSub("Pub/Sub\ncampaign-steps")

        with Cluster("Worker  ·  flock-worker  ·  Cloud Run  ·  async", graph_attr=CLUSTER):
            worker = Run(
                "Scout → Inka → Harvest\n"
                "Ledge gate → Stella → Ad Kit\n"
                "one receipt per step"
            )

        with Cluster("Vertex AI  ·  required + bonus", graph_attr={**CLUSTER, "bgcolor": "#f3ece8"}):
            models = VertexAI(
                "Search + Maps  ·  Veo 3.1\n"
                "Gemini Image  ·  TTS EN+Indic\n"
                "Lyria  ·  Gemma 3"
            )

        with Cluster("Record  ·  identity  ·  memory  ·  traces", graph_attr=CLUSTER):
            fs = Firestore("Firestore\nreceipts")
            gcs = GCS("Cloud Storage\nmedia")
            memory = AIPlatform("Memory Bank")
            trace = Monitoring("Cloud Trace\nOpenTelemetry")
            fs >> Edge(color=ASH, style="dashed") >> gcs
            gcs >> Edge(color=ASH, style="dashed") >> memory
            memory >> Edge(color=ASH, style="dashed") >> trace

        with Cluster("Delivery  ·  flock never posts", graph_attr=CLUSTER):
            paste = Run("Paste kit  /k")
            land = Run("Landing  /l\nconsent + UTM")
            dash = Monitoring("Observatory  /dash\ntokens · tools · cost")
            paste >> Edge(color=ASH, style="dashed") >> land
            land >> Edge(color=ASH, style="dashed") >> dash

        shop >> Edge(color=INK, label="listing") >> roost
        roost >> Edge(color=INK) >> flo
        flo >> Edge(color=INK) >> gemini
        flo >> Edge(color=PINK) >> armor
        flo >> Edge(color=ASH, style="dashed") >> card
        gemini >> Edge(color=INK, label="YES") >> bus
        bus >> Edge(color=INK) >> worker
        worker >> Edge(color=PINK, style="dashed", label="models") >> models
        worker >> Edge(color=INK) >> paste
        worker >> Edge(color=INK) >> land
        worker >> Edge(color=ASH, style="dashed") >> fs
        worker >> Edge(color=ASH, style="dashed") >> gcs
        flo >> Edge(color=ASH, style="dashed") >> memory
        flo >> Edge(color=ASH, style="dashed") >> trace

    png = Path(str(OUT) + ".png")
    if not png.is_file():
        raise SystemExit(f"diagram was not written: {png}")
    static = ROOT / "app" / "static" / "flock" / "architecture.png"
    static.write_bytes(png.read_bytes())
    return png


if __name__ == "__main__":
    print(main())
