import json
import math
import os
import random
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk
from openai import OpenAI
from pydantic import BaseModel, Field


# -----------------------------
# Data models for the canvas
# -----------------------------


class ToolMode(str, Enum):
    SELECT = "select"
    AGENT = "agent"
    ARTIFACT = "artifact"
    LOOPTIE = "looptie"
    SWIRL = "swirl"
    KNOT = "knot"


@dataclass
class AgentNode:
    node_id: str
    name: str
    x: float
    y: float
    role: str = "generalist"
    recursion_depth: int = 0
    prompt_seed: str = ""
    phase: float = 0.0
    entropy_bias: float = 0.5
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class ArtifactNode:
    artifact_id: str
    text: str
    x: float
    y: float
    weight: float = 1.0
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class EdgeLink:
    edge_id: str
    source_id: str
    target_id: str
    tie_strength: float = 1.0
    phase_lag: float = 0.0
    curve: float = 40.0
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class KnotNode:
    knot_id: str
    x: float
    y: float
    sync_threshold: float = 0.72
    attached_agent_ids: List[str] = field(default_factory=list)
    canvas_items: List[int] = field(default_factory=list)


# -----------------------------
# Structured output for compiler
# -----------------------------


class RuntimeNode(BaseModel):
    id: str
    kind: str
    label: str
    system_prompt: str
    tools: List[str] = Field(default_factory=list)
    recursion_budget: int = 0
    entropy_target: float = 0.5


class RuntimeEdge(BaseModel):
    id: str
    source: str
    target: str
    interaction: str
    strength: float
    phase_lag: float
    resonance: float
    notes: str


class RuntimePolicy(BaseModel):
    entropy_min: float
    entropy_max: float
    compile_mode: str
    creativity_strategy: str
    sync_rule: str


class RuntimeGraphSpec(BaseModel):
    title: str
    summary: str
    nodes: List[RuntimeNode]
    edges: List[RuntimeEdge]
    policies: RuntimePolicy
    compile_notes: List[str]


# -----------------------------
# Main app
# -----------------------------


class LooptieStudio(ctk.CTk):
    AGENT_RADIUS = 28
    ARTIFACT_W = 160
    ARTIFACT_H = 72
    KNOT_RADIUS = 12

    def __init__(self):
        super().__init__()
        self.title("Looptie Studio — Human-Organized Entropy")
        self.geometry("1440x920")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.client: Optional[OpenAI] = None
        self.mode: ToolMode = ToolMode.SELECT
        self.selected_canvas_id: Optional[int] = None
        self.dragging_id: Optional[int] = None
        self.drag_offset = (0.0, 0.0)
        self.pending_link_start: Optional[str] = None

        self.node_counter = 1
        self.artifact_counter = 1
        self.edge_counter = 1
        self.knot_counter = 1

        self.agents: Dict[str, AgentNode] = {}
        self.artifacts: Dict[str, ArtifactNode] = {}
        self.edges: Dict[str, EdgeLink] = {}
        self.knots: Dict[str, KnotNode] = {}

        self.canvas_to_model: Dict[int, Tuple[str, str]] = {}

        self._build_ui()
        self._log("Ready. Place agents, artifacts, loopties, swirls, and knots.")

    # ---------- UI ----------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left.grid_propagate(False)

        self.center = ctk.CTkFrame(self, corner_radius=0)
        self.center.grid(row=0, column=1, sticky="nsew")
        self.center.grid_rowconfigure(0, weight=1)
        self.center.grid_columnconfigure(0, weight=1)

        self.right = ctk.CTkFrame(self, width=360, corner_radius=0)
        self.right.grid(row=0, column=2, sticky="nsew")
        self.right.grid_propagate(False)

        # Left controls
        ctk.CTkLabel(self.left, text="Looptie Tools", font=ctk.CTkFont(size=22, weight="bold")).pack(
            padx=16, pady=(18, 10), anchor="w"
        )

        self.tool_buttons = {}
        for label, mode in [
            ("Select / Move", ToolMode.SELECT),
            ("Add Agent", ToolMode.AGENT),
            ("Add Artifact", ToolMode.ARTIFACT),
            ("Draw Looptie", ToolMode.LOOPTIE),
            ("Add Swirl", ToolMode.SWIRL),
            ("Add Knot", ToolMode.KNOT),
        ]:
            btn = ctk.CTkButton(self.left, text=label, command=lambda m=mode: self.set_mode(m))
            btn.pack(fill="x", padx=16, pady=6)
            self.tool_buttons[mode] = btn

        ctk.CTkLabel(self.left, text="Agent defaults", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=16, pady=(20, 6), anchor="w"
        )
        self.agent_role_var = ctk.StringVar(value="generalist")
        self.agent_name_var = ctk.StringVar(value="")
        self.agent_prompt_var = ctk.StringVar(value="")
        self.agent_entropy_var = ctk.DoubleVar(value=0.50)
        self.agent_phase_var = ctk.DoubleVar(value=0.0)

        ctk.CTkEntry(self.left, textvariable=self.agent_name_var, placeholder_text="Next agent label").pack(
            fill="x", padx=16, pady=5
        )
        ctk.CTkEntry(self.left, textvariable=self.agent_role_var, placeholder_text="Role").pack(
            fill="x", padx=16, pady=5
        )
        ctk.CTkEntry(self.left, textvariable=self.agent_prompt_var, placeholder_text="Prompt seed").pack(
            fill="x", padx=16, pady=5
        )
        ctk.CTkLabel(self.left, text="Entropy bias").pack(padx=16, pady=(10, 0), anchor="w")
        ctk.CTkSlider(self.left, from_=0.0, to=1.0, variable=self.agent_entropy_var).pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(self.left, text="Initial phase").pack(padx=16, pady=(10, 0), anchor="w")
        ctk.CTkSlider(self.left, from_=-math.pi, to=math.pi, variable=self.agent_phase_var).pack(fill="x", padx=16, pady=6)

        # Center canvas
        self.canvas = tk.Canvas(self.center, bg="#121417", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self._draw_grid()

        # Right panel
        ctk.CTkLabel(self.right, text="Compiler", font=ctk.CTkFont(size=22, weight="bold")).pack(
            padx=16, pady=(18, 10), anchor="w"
        )

        self.api_key_var = ctk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
        self.model_var = ctk.StringVar(value="gpt-5.4")
        self.reasoning_var = ctk.StringVar(value="medium")
        self.temperature_var = ctk.DoubleVar(value=0.7)
        self.entropy_min_var = ctk.DoubleVar(value=0.25)
        self.entropy_max_var = ctk.DoubleVar(value=0.78)

        ctk.CTkEntry(self.right, textvariable=self.api_key_var, show="*", placeholder_text="OPENAI_API_KEY").pack(
            fill="x", padx=16, pady=6
        )
        ctk.CTkEntry(self.right, textvariable=self.model_var, placeholder_text="Model").pack(
            fill="x", padx=16, pady=6
        )
        ctk.CTkEntry(self.right, textvariable=self.reasoning_var, placeholder_text="Reasoning effort").pack(
            fill="x", padx=16, pady=6
        )

        ctk.CTkLabel(self.right, text="Entropy bounds for creativity").pack(padx=16, pady=(14, 2), anchor="w")
        ctk.CTkLabel(self.right, text="Lower bound").pack(padx=16, pady=(6, 0), anchor="w")
        ctk.CTkSlider(self.right, from_=0.0, to=1.0, variable=self.entropy_min_var).pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(self.right, text="Upper bound").pack(padx=16, pady=(6, 0), anchor="w")
        ctk.CTkSlider(self.right, from_=0.0, to=1.0, variable=self.entropy_max_var).pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(self.right, text="Sampling temperature").pack(padx=16, pady=(10, 0), anchor="w")
        ctk.CTkSlider(self.right, from_=0.0, to=1.5, variable=self.temperature_var).pack(fill="x", padx=16, pady=4)

        btn_frame = ctk.CTkFrame(self.right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=10)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_frame, text="Compile Local", command=self.compile_local).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(btn_frame, text="Compile with GPT", command=self.compile_with_gpt).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(btn_frame, text="Export JSON", command=self.export_json).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(btn_frame, text="Clear Canvas", command=self.clear_canvas).grid(row=1, column=1, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(self.right, text="Runtime graph").pack(padx=16, pady=(12, 4), anchor="w")
        self.output_box = ctk.CTkTextbox(self.right, width=328, height=300, wrap="word")
        self.output_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        ctk.CTkLabel(self.right, text="Log").pack(padx=16, pady=(2, 4), anchor="w")
        self.log_box = ctk.CTkTextbox(self.right, width=328, height=180, wrap="word")
        self.log_box.pack(fill="both", expand=False, padx=16, pady=(0, 16))

        self.set_mode(ToolMode.SELECT)

    # ---------- Canvas helpers ----------

    def _draw_grid(self) -> None:
        w = 2000
        h = 2000
        step = 40
        for x in range(0, w, step):
            self.canvas.create_line(x, 0, x, h, fill="#1c2024")
        for y in range(0, h, step):
            self.canvas.create_line(0, y, w, y, fill="#1c2024")

    def _log(self, msg: str) -> None:
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def set_mode(self, mode: ToolMode) -> None:
        self.mode = mode
        for m, btn in self.tool_buttons.items():
            btn.configure(fg_color=("#1f6aa5" if m == mode else "#3B8ED0"))
        self._log(f"Mode: {mode.value}")

    def _new_agent_name(self) -> str:
        base = self.agent_name_var.get().strip() or f"Agent {self.node_counter}"
        self.node_counter += 1
        return base

    def _nearest_entity(self, x: float, y: float, kinds: Tuple[str, ...] = ("agent", "artifact", "knot")) -> Optional[Tuple[str, str]]:
        best = None
        best_d = 1e9
        for agent_id, agent in self.agents.items():
            if "agent" in kinds:
                d = math.dist((x, y), (agent.x, agent.y))
                if d < best_d:
                    best = ("agent", agent_id)
                    best_d = d
        for artifact_id, artifact in self.artifacts.items():
            if "artifact" in kinds:
                d = math.dist((x, y), (artifact.x, artifact.y))
                if d < best_d:
                    best = ("artifact", artifact_id)
                    best_d = d
        for knot_id, knot in self.knots.items():
            if "knot" in kinds:
                d = math.dist((x, y), (knot.x, knot.y))
                if d < best_d:
                    best = ("knot", knot_id)
                    best_d = d
        return best if best_d < 80 else None

    def _agent_color(self, entropy_bias: float) -> str:
        # Subtle hue shift using entropy bias.
        if entropy_bias < 0.33:
            return "#3b82f6"
        if entropy_bias < 0.66:
            return "#8b5cf6"
        return "#f97316"

    def _draw_agent(self, agent: AgentNode) -> None:
        x, y, r = agent.x, agent.y, self.AGENT_RADIUS
        color = self._agent_color(agent.entropy_bias)
        oval = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="#d1d5db", width=2)
        text = self.canvas.create_text(x, y, text=agent.name, fill="white", width=110, font=("Arial", 10, "bold"))
        subtitle = self.canvas.create_text(x, y + 44, text=agent.role, fill="#b7c0c8", font=("Arial", 9))
        agent.canvas_items = [oval, text, subtitle]
        for item_id in agent.canvas_items:
            self.canvas_to_model[item_id] = ("agent", agent.node_id)

    def _draw_artifact(self, artifact: ArtifactNode) -> None:
        x, y = artifact.x, artifact.y
        w, h = self.ARTIFACT_W, self.ARTIFACT_H
        rect = self.canvas.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                            fill="#1f2937", outline="#facc15", width=2)
        text = self.canvas.create_text(x, y, text=artifact.text, fill="#fde68a", width=w - 16, font=("Arial", 10))
        artifact.canvas_items = [rect, text]
        for item_id in artifact.canvas_items:
            self.canvas_to_model[item_id] = ("artifact", artifact.artifact_id)

    def _draw_looptie(self, edge: EdgeLink) -> None:
        a = self.agents[edge.source_id]
        b = self.agents[edge.target_id]
        dx = b.x - a.x
        dy = b.y - a.y
        dist = max(math.hypot(dx, dy), 1.0)
        nx, ny = -dy / dist, dx / dist
        cx = (a.x + b.x) / 2 + nx * edge.curve
        cy = (a.y + b.y) / 2 + ny * edge.curve
        line = self.canvas.create_line(a.x, a.y, cx, cy, b.x, b.y, smooth=True, splinesteps=36,
                                       width=max(2, int(2 + edge.tie_strength * 2)), fill="#7dd3fc")
        label = self.canvas.create_text(cx, cy - 14, text=f"τ={edge.phase_lag:.2f}", fill="#93c5fd", font=("Arial", 9))
        edge.canvas_items = [line, label]
        for item_id in edge.canvas_items:
            self.canvas_to_model[item_id] = ("edge", edge.edge_id)
        self.canvas.tag_lower(line)

    def _draw_swirl(self, agent: AgentNode) -> None:
        loops = max(1, agent.recursion_depth)
        for n in range(loops):
            pad = 12 + n * 7
            arc = self.canvas.create_arc(
                agent.x - self.AGENT_RADIUS - pad,
                agent.y - self.AGENT_RADIUS - pad,
                agent.x + self.AGENT_RADIUS + pad,
                agent.y + self.AGENT_RADIUS + pad,
                start=35 + n * 18,
                extent=260,
                style=tk.ARC,
                outline="#f472b6",
                width=2,
            )
            self.canvas_to_model[arc] = ("agent", agent.node_id)
            agent.canvas_items.append(arc)

    def _draw_knot(self, knot: KnotNode) -> None:
        x, y, r = knot.x, knot.y, self.KNOT_RADIUS
        circle = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#22c55e", outline="#dcfce7", width=2)
        cross1 = self.canvas.create_line(x - r, y - r, x + r, y + r, fill="#dcfce7", width=2)
        cross2 = self.canvas.create_line(x - r, y + r, x + r, y - r, fill="#dcfce7", width=2)
        knot.canvas_items = [circle, cross1, cross2]
        for item_id in knot.canvas_items:
            self.canvas_to_model[item_id] = ("knot", knot.knot_id)

    # ---------- Event handlers ----------

    def on_canvas_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        clicked = self.canvas.find_withtag("current")
        item_id = clicked[0] if clicked else None

        if self.mode == ToolMode.AGENT:
            self.add_agent(x, y)
            return
        if self.mode == ToolMode.ARTIFACT:
            self.add_artifact(x, y)
            return
        if self.mode == ToolMode.KNOT:
            self.add_knot(x, y)
            return
        if self.mode == ToolMode.SWIRL:
            target = self._nearest_entity(x, y, ("agent",))
            if target:
                self.add_swirl(target[1])
            return
        if self.mode == ToolMode.LOOPTIE:
            target = self._nearest_entity(x, y, ("agent",))
            if not target:
                return
            if self.pending_link_start is None:
                self.pending_link_start = target[1]
                self._log(f"Looptie start: {target[1]}")
            else:
                if self.pending_link_start != target[1]:
                    self.add_looptie(self.pending_link_start, target[1])
                self.pending_link_start = None
            return

        if item_id and item_id in self.canvas_to_model:
            self.selected_canvas_id = item_id
            kind, obj_id = self.canvas_to_model[item_id]
            self.dragging_id = item_id
            if kind == "agent":
                agent = self.agents[obj_id]
                self.drag_offset = (agent.x - x, agent.y - y)
            elif kind == "artifact":
                artifact = self.artifacts[obj_id]
                self.drag_offset = (artifact.x - x, artifact.y - y)
            elif kind == "knot":
                knot = self.knots[obj_id]
                self.drag_offset = (knot.x - x, knot.y - y)
            self._show_selection(kind, obj_id)
        else:
            self.selected_canvas_id = None
            self.dragging_id = None

    def on_canvas_drag(self, event) -> None:
        if self.mode != ToolMode.SELECT or not self.dragging_id:
            return
        if self.dragging_id not in self.canvas_to_model:
            return
        kind, obj_id = self.canvas_to_model[self.dragging_id]
        x = self.canvas.canvasx(event.x) + self.drag_offset[0]
        y = self.canvas.canvasy(event.y) + self.drag_offset[1]

        if kind == "agent":
            self.agents[obj_id].x = x
            self.agents[obj_id].y = y
        elif kind == "artifact":
            self.artifacts[obj_id].x = x
            self.artifacts[obj_id].y = y
        elif kind == "knot":
            self.knots[obj_id].x = x
            self.knots[obj_id].y = y
        self.redraw_scene()

    def on_canvas_release(self, _event) -> None:
        self.dragging_id = None

    def on_canvas_double_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        target = self._nearest_entity(x, y)
        if not target:
            return
        kind, obj_id = target
        if kind == "artifact":
            text = self._simple_prompt_dialog("Artifact text", self.artifacts[obj_id].text)
            if text:
                self.artifacts[obj_id].text = text
        elif kind == "agent":
            name = self._simple_prompt_dialog("Agent label", self.agents[obj_id].name)
            if name:
                self.agents[obj_id].name = name
        self.redraw_scene()

    # ---------- CRUD ----------

    def add_agent(self, x: float, y: float) -> None:
        node_id = f"agent_{self.node_counter}"
        agent = AgentNode(
            node_id=node_id,
            name=self._new_agent_name(),
            x=x,
            y=y,
            role=self.agent_role_var.get().strip() or "generalist",
            recursion_depth=0,
            prompt_seed=self.agent_prompt_var.get().strip(),
            phase=self.agent_phase_var.get(),
            entropy_bias=self.agent_entropy_var.get(),
        )
        self.agents[node_id] = agent
        self._draw_agent(agent)
        self._log(f"Added agent {node_id}")

    def add_artifact(self, x: float, y: float) -> None:
        artifact_id = f"artifact_{self.artifact_counter}"
        self.artifact_counter += 1
        text = self._simple_prompt_dialog("Artifact prompt", "idea, image cue, or note") or "untitled artifact"
        artifact = ArtifactNode(artifact_id=artifact_id, text=text, x=x, y=y)
        self.artifacts[artifact_id] = artifact
        self._draw_artifact(artifact)
        self._log(f"Added artifact {artifact_id}")

    def add_looptie(self, source_id: str, target_id: str) -> None:
        edge_id = f"edge_{self.edge_counter}"
        self.edge_counter += 1
        a = self.agents[source_id]
        b = self.agents[target_id]
        dist = math.dist((a.x, a.y), (b.x, b.y))
        edge = EdgeLink(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            tie_strength=max(0.2, min(1.5, 220.0 / max(120.0, dist))),
            phase_lag=random.uniform(-1.0, 1.0),
            curve=random.choice([30.0, 45.0, 65.0, -35.0, -55.0]),
        )
        self.edges[edge_id] = edge
        self._draw_looptie(edge)
        self._log(f"Added looptie {edge_id}: {source_id} -> {target_id}")

    def add_swirl(self, agent_id: str) -> None:
        self.agents[agent_id].recursion_depth += 1
        self.redraw_scene()
        self._log(f"Increased swirl recursion on {agent_id} to {self.agents[agent_id].recursion_depth}")

    def add_knot(self, x: float, y: float) -> None:
        knot_id = f"knot_{self.knot_counter}"
        self.knot_counter += 1
        nearby_agents = [
            aid for aid, agent in self.agents.items() if math.dist((x, y), (agent.x, agent.y)) < 180
        ]
        knot = KnotNode(knot_id=knot_id, x=x, y=y, attached_agent_ids=nearby_agents)
        self.knots[knot_id] = knot
        self._draw_knot(knot)
        self._log(f"Added knot {knot_id} with {len(nearby_agents)} attached agents")

    def clear_canvas(self) -> None:
        self.canvas.delete("all")
        self.canvas_to_model.clear()
        self.agents.clear()
        self.artifacts.clear()
        self.edges.clear()
        self.knots.clear()
        self.pending_link_start = None
        self._draw_grid()
        self._log("Canvas cleared")
        self.output_box.delete("1.0", "end")

    def redraw_scene(self) -> None:
        self.canvas.delete("all")
        self.canvas_to_model.clear()
        self._draw_grid()
        for edge in self.edges.values():
            self._draw_looptie(edge)
        for artifact in self.artifacts.values():
            self._draw_artifact(artifact)
        for agent in self.agents.values():
            agent.canvas_items = []
            self._draw_agent(agent)
        for agent in self.agents.values():
            if agent.recursion_depth > 0:
                self._draw_swirl(agent)
        for knot in self.knots.values():
            self._draw_knot(knot)
            self._draw_knot_links(knot)

    def _draw_knot_links(self, knot: KnotNode) -> None:
        for agent_id in knot.attached_agent_ids:
            if agent_id in self.agents:
                a = self.agents[agent_id]
                line = self.canvas.create_line(knot.x, knot.y, a.x, a.y, dash=(3, 4), fill="#86efac", width=2)
                self.canvas_to_model[line] = ("knot", knot.knot_id)
                self.canvas.tag_lower(line)

    # ---------- Selection panel ----------

    def _show_selection(self, kind: str, obj_id: str) -> None:
        info = {
            "kind": kind,
            "id": obj_id,
        }
        if kind == "agent":
            a = self.agents[obj_id]
            info.update({
                "name": a.name,
                "role": a.role,
                "phase": round(a.phase, 3),
                "entropy_bias": round(a.entropy_bias, 3),
                "swirl_depth": a.recursion_depth,
            })
        elif kind == "artifact":
            art = self.artifacts[obj_id]
            info.update({"text": art.text, "weight": art.weight})
        elif kind == "knot":
            knot = self.knots[obj_id]
            info.update({"sync_threshold": knot.sync_threshold, "agents": knot.attached_agent_ids})
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", json.dumps(info, indent=2))

    # ---------- Semantics and compiler ----------

    def _artifact_prompts_for_agent(self, agent: AgentNode, radius: float = 220.0) -> List[str]:
        prompts = []
        for artifact in self.artifacts.values():
            d = math.dist((agent.x, agent.y), (artifact.x, artifact.y))
            if d <= radius:
                prompts.append(f"[{artifact.weight:.2f}] {artifact.text}")
        return prompts

    def _distance_affinity(self, a: AgentNode, b: AgentNode, sigma: float = 220.0) -> float:
        d = math.dist((a.x, a.y), (b.x, b.y))
        return math.exp(-(d ** 2) / (2 * sigma ** 2))

    def _phase_resonance(self, a: AgentNode, b: AgentNode, lag: float) -> float:
        return 0.5 + 0.5 * math.cos(a.phase - b.phase - lag)

    def _human_organized_entropy(self) -> float:
        if not self.agents:
            return 0.0
        values = []
        for agent in self.agents.values():
            local_types = [1.0]  # self mass
            local_types.extend([edge.tie_strength for edge in self.edges.values() if edge.source_id == agent.node_id or edge.target_id == agent.node_id])
            local_types.extend([0.6 for knot in self.knots.values() if agent.node_id in knot.attached_agent_ids])
            local_types.extend([0.8 for art in self.artifacts.values() if math.dist((agent.x, agent.y), (art.x, art.y)) < 220])
            s = sum(local_types)
            probs = [v / s for v in local_types if s > 0]
            h = -sum(p * math.log(max(p, 1e-9), 2) for p in probs)
            values.append(h / max(1.0, math.log(len(probs) + 1, 2)))
        return sum(values) / len(values)

    def _spatial_semantics(self) -> Dict[str, float]:
        if len(self.agents) < 2:
            return {"mean_affinity": 0.0, "mean_resonance": 0.0}
        aff = []
        res = []
        for edge in self.edges.values():
            a = self.agents[edge.source_id]
            b = self.agents[edge.target_id]
            aff.append(self._distance_affinity(a, b))
            res.append(self._phase_resonance(a, b, edge.phase_lag))
        if not aff:
            ids = list(self.agents.keys())
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a = self.agents[ids[i]]
                    b = self.agents[ids[j]]
                    aff.append(self._distance_affinity(a, b))
                    res.append(self._phase_resonance(a, b, 0.0))
        return {
            "mean_affinity": sum(aff) / max(1, len(aff)),
            "mean_resonance": sum(res) / max(1, len(res)),
        }

    def _compile_scene_dict(self) -> Dict:
        entropy = self._human_organized_entropy()
        semantics = self._spatial_semantics()

        nodes = []
        for agent in self.agents.values():
            artifact_prompts = self._artifact_prompts_for_agent(agent)
            system_prompt = (
                f"Role: {agent.role}. "
                f"Human-organized entropy target: {agent.entropy_bias:.2f}. "
                f"Swirl recursion budget: {agent.recursion_depth}. "
                f"Prompt seed: {agent.prompt_seed or 'none'}. "
                f"Nearby artifacts: {' | '.join(artifact_prompts) if artifact_prompts else 'none'}."
            )
            nodes.append(
                {
                    "id": agent.node_id,
                    "kind": "agent",
                    "label": agent.name,
                    "role": agent.role,
                    "x": round(agent.x, 2),
                    "y": round(agent.y, 2),
                    "phase": round(agent.phase, 3),
                    "recursion_budget": agent.recursion_depth,
                    "entropy_target": round(agent.entropy_bias, 3),
                    "artifact_prompts": artifact_prompts,
                    "system_prompt": system_prompt,
                    "tools": ["reason", "summarize", "reflect"] + (["deploy"] if "deploy" in agent.role.lower() else []),
                }
            )

        artifact_nodes = []
        for art in self.artifacts.values():
            artifact_nodes.append(
                {
                    "id": art.artifact_id,
                    "kind": "artifact",
                    "label": art.text[:48],
                    "x": round(art.x, 2),
                    "y": round(art.y, 2),
                    "weight": round(art.weight, 3),
                    "prompt": art.text,
                }
            )

        edges = []
        for edge in self.edges.values():
            a = self.agents[edge.source_id]
            b = self.agents[edge.target_id]
            resonance = self._phase_resonance(a, b, edge.phase_lag)
            affinity = self._distance_affinity(a, b)
            edges.append(
                {
                    "id": edge.edge_id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "interaction": "looptie",
                    "strength": round(edge.tie_strength, 3),
                    "phase_lag": round(edge.phase_lag, 3),
                    "curve": round(edge.curve, 2),
                    "spatial_affinity": round(affinity, 3),
                    "resonance": round(resonance, 3),
                    "notes": "phase-aware recurrent exchange",
                }
            )

        knot_specs = []
        for knot in self.knots.values():
            knot_specs.append(
                {
                    "id": knot.knot_id,
                    "kind": "knot",
                    "x": round(knot.x, 2),
                    "y": round(knot.y, 2),
                    "sync_threshold": round(knot.sync_threshold, 3),
                    "attached_agent_ids": knot.attached_agent_ids,
                }
            )

        compile_mode = "creative_band" if self.entropy_min_var.get() < entropy < self.entropy_max_var.get() else "rebalance"
        scene = {
            "concepts": {
                "human_organized_entropy": round(entropy, 4),
                "spatial_semantics": semantics,
                "entropy_bounds": {
                    "min": round(self.entropy_min_var.get(), 3),
                    "max": round(self.entropy_max_var.get(), 3),
                    "status": "inside" if self.entropy_min_var.get() <= entropy <= self.entropy_max_var.get() else "outside",
                },
            },
            "nodes": nodes,
            "artifacts": artifact_nodes,
            "edges": edges,
            "knots": knot_specs,
            "compiler_hints": {
                "goal": "Compile canvas geometry into a runtime graph for agentized LLM orchestration.",
                "creativity_strategy": "Preserve ambiguity inside entropy band while binding deployment paths to knots.",
                "phase_lag_resonance": "Use phase lag to delay synchronization until ideas mature.",
                "artifact_placement_as_prompt": "Use nearby artifacts as prompt priors for adjacent agents.",
                "compile_mode": compile_mode,
            },
        }
        return scene

    def compile_local(self) -> None:
        scene = self._compile_scene_dict()
        runtime = self._heuristic_runtime_graph(scene)
        self._write_output(runtime.model_dump_json(indent=2))
        self._log("Local compiler produced a runtime graph")

    def _heuristic_runtime_graph(self, scene: Dict) -> RuntimeGraphSpec:
        nodes: List[RuntimeNode] = []
        for node in scene["nodes"]:
            nodes.append(
                RuntimeNode(
                    id=node["id"],
                    kind=node["kind"],
                    label=node["label"],
                    system_prompt=node["system_prompt"],
                    tools=node["tools"],
                    recursion_budget=node["recursion_budget"],
                    entropy_target=node["entropy_target"],
                )
            )

        for knot in scene["knots"]:
            nodes.append(
                RuntimeNode(
                    id=knot["id"],
                    kind="knot",
                    label=f"Knot {knot['id']}",
                    system_prompt=(
                        "Act as a synchronization barrier. Merge only when inbound resonance "
                        f"exceeds {knot['sync_threshold']:.2f}."
                    ),
                    tools=["gate", "merge", "approve"],
                    recursion_budget=0,
                    entropy_target=0.2,
                )
            )

        edges: List[RuntimeEdge] = []
        for edge in scene["edges"]:
            edges.append(
                RuntimeEdge(
                    id=edge["id"],
                    source=edge["source"],
                    target=edge["target"],
                    interaction=edge["interaction"],
                    strength=edge["strength"],
                    phase_lag=edge["phase_lag"],
                    resonance=edge["resonance"],
                    notes=edge["notes"],
                )
            )

        for knot in scene["knots"]:
            for agent_id in knot["attached_agent_ids"]:
                edges.append(
                    RuntimeEdge(
                        id=f"{knot['id']}_{agent_id}",
                        source=agent_id,
                        target=knot["id"],
                        interaction="knot_sync",
                        strength=0.8,
                        phase_lag=0.0,
                        resonance=0.8,
                        notes="barrier synchronization path",
                    )
                )

        policy = RuntimePolicy(
            entropy_min=scene["concepts"]["entropy_bounds"]["min"],
            entropy_max=scene["concepts"]["entropy_bounds"]["max"],
            compile_mode=scene["compiler_hints"]["compile_mode"],
            creativity_strategy=scene["compiler_hints"]["creativity_strategy"],
            sync_rule="Knot nodes must receive all required inbound updates before deployment edges may fire.",
        )
        notes = [
            f"Human-organized entropy = {scene['concepts']['human_organized_entropy']:.3f}",
            f"Mean spatial affinity = {scene['concepts']['spatial_semantics']['mean_affinity']:.3f}",
            f"Mean phase-lag resonance = {scene['concepts']['spatial_semantics']['mean_resonance']:.3f}",
            "Artifacts were attached as prompt priors to nearby agents.",
            "Swirl recursion was compiled into recursion_budget.",
        ]

        return RuntimeGraphSpec(
            title="Looptie Runtime Graph",
            summary="A compiled runtime graph from a human-organized entropy canvas.",
            nodes=nodes,
            edges=edges,
            policies=policy,
            compile_notes=notes,
        )

    def compile_with_gpt(self) -> None:
        try:
            api_key = self.api_key_var.get().strip() or os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError("No API key found. Set OPENAI_API_KEY or paste it into the API field.")
            self.client = OpenAI(api_key=api_key)
            scene = self._compile_scene_dict()
            system_prompt = (
                "You are a compiler for a spatial multi-agent interface. "
                "Turn human-organized entropy, spatial semantics, looptie grammar, swirl recursion, "
                "knot synchronization, phase-lag resonance, artifact placement as prompt, and entropy bounds "
                "for creativity into a precise runtime graph. Preserve the artistic topology but output a strict runtime spec."
            )
            response = self.client.responses.parse(
                model=self.model_var.get().strip() or "gpt-5.4",
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Compile this canvas into a runtime graph. Use knot nodes as explicit sync barriers.\n\n"
                            + json.dumps(scene, indent=2)
                        ),
                    },
                ],
                text_format=RuntimeGraphSpec,
                reasoning={"effort": self.reasoning_var.get().strip() or "medium"},
                temperature=self.temperature_var.get(),
            )
            compiled = response.output_parsed
            self._write_output(compiled.model_dump_json(indent=2))
            self._log("GPT compiler produced a runtime graph")
        except Exception as exc:
            self._log(f"Compile error: {exc}")
            self._write_output(json.dumps({"error": str(exc)}, indent=2))

    def export_json(self) -> None:
        scene = self._compile_scene_dict()
        export = {
            "canvas": scene,
            "local_runtime": self._heuristic_runtime_graph(scene).model_dump(),
        }
        file_path = os.path.join(os.getcwd(), "looptie_export.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)
        self._log(f"Exported to {file_path}")
        self._write_output(json.dumps(export, indent=2))

    # ---------- Utility ----------

    def _write_output(self, text: str) -> None:
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", text)

    def _simple_prompt_dialog(self, title: str, default: str = "") -> Optional[str]:
        dialog = ctk.CTkInputDialog(text=title, title=title)
        value = dialog.get_input()
        if value is None:
            return default if default else None
        value = value.strip()
        return value or default


def main() -> None:
    app = LooptieStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
