import json
import math
import os
import random
import time
import tkinter as tk
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tkinter import filedialog, messagebox

import customtkinter as ctk
from openai import OpenAI
from pydantic import BaseModel, Field


# ============================================================
# Spatial compiler primitives
# ============================================================


class ToolMode(str, Enum):
    SELECT = "select"
    AGENT = "agent"
    ARTIFACT = "artifact"
    LOOPTIE = "looptie"
    SWIRL = "swirl"
    KNOT = "knot"
    FIELD = "field"


@dataclass
class AgentNode:
    node_id: str
    name: str
    x: float
    y: float
    role: str = "generalist"
    prompt_seed: str = ""
    phase: float = 0.0
    frequency: float = 0.03
    entropy_bias: float = 0.50
    recursion_depth: int = 0
    activation: float = 0.0
    coherence: float = 0.50
    halo_strength: float = 0.50
    allowed_tools: List[str] = field(default_factory=lambda: ["reason", "reflect", "summarize"])
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class ArtifactNode:
    artifact_id: str
    text: str
    x: float
    y: float
    weight: float = 1.0
    kind: str = "prompt"
    prompt_mode: str = "semantic"
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class EdgeLink:
    edge_id: str
    source_id: str
    target_id: str
    tie_strength: float = 1.0
    phase_lag: float = 0.0
    curve: float = 40.0
    bandwidth: float = 1.0
    recurrence: float = 0.5
    interaction: str = "looptie"
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class KnotNode:
    knot_id: str
    x: float
    y: float
    sync_threshold: float = 0.72
    quorum: int = 2
    attached_agent_ids: List[str] = field(default_factory=list)
    canvas_items: List[int] = field(default_factory=list)


@dataclass
class FieldZone:
    zone_id: str
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    entropy_min: float = 0.25
    entropy_max: float = 0.78
    theme: str = "studio"
    canvas_items: List[int] = field(default_factory=list)


# ============================================================
# Runtime spec models for local compiler and GPT compiler
# ============================================================


class RuntimeNode(BaseModel):
    id: str
    kind: str
    label: str
    role: str
    system_prompt: str
    tools: List[str] = Field(default_factory=list)
    recursion_budget: int = 0
    entropy_target: float = 0.5
    phase: float = 0.0
    field_membership: List[str] = Field(default_factory=list)
    prompt_artifacts: List[str] = Field(default_factory=list)


class RuntimeEdge(BaseModel):
    id: str
    source: str
    target: str
    interaction: str
    strength: float
    phase_lag: float
    bandwidth: float
    recurrence: float
    resonance: float
    notes: str


class RuntimeBarrier(BaseModel):
    id: str
    threshold: float
    quorum: int
    attached_agents: List[str]
    release_rule: str


class RuntimeScheduleStep(BaseModel):
    stage: str
    node_ids: List[str]
    entry_criterion: str
    exit_criterion: str


class RuntimePolicy(BaseModel):
    entropy_min: float
    entropy_max: float
    creativity_mode: str
    sync_rule: str
    deployment_rule: str
    equations: List[str] = Field(default_factory=list)


class RuntimeGraphSpec(BaseModel):
    title: str
    summary: str
    nodes: List[RuntimeNode]
    edges: List[RuntimeEdge]
    barriers: List[RuntimeBarrier]
    schedule: List[RuntimeScheduleStep]
    policies: RuntimePolicy
    compiler_notes: List[str]


# ============================================================
# Main application
# ============================================================


class AdvancedLooptieStudio(ctk.CTk):
    AGENT_RADIUS = 30
    KNOT_RADIUS = 13
    ARTIFACT_W = 170
    ARTIFACT_H = 76

    def __init__(self):
        super().__init__()
        self.title("Looptie Studio Pro — Resonance Canvas")
        self.geometry("1640x980")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.client: Optional[OpenAI] = None
        self.mode: ToolMode = ToolMode.SELECT
        self.pending_link_start: Optional[str] = None
        self.pending_field_start: Optional[Tuple[float, float]] = None
        self.selected: Optional[Tuple[str, str]] = None
        self.dragging_ref: Optional[Tuple[str, str]] = None
        self.drag_offset = (0.0, 0.0)
        self.canvas_to_model: Dict[int, Tuple[str, str]] = {}

        self.agent_counter = 1
        self.artifact_counter = 1
        self.edge_counter = 1
        self.knot_counter = 1
        self.zone_counter = 1

        self.agents: Dict[str, AgentNode] = {}
        self.artifacts: Dict[str, ArtifactNode] = {}
        self.edges: Dict[str, EdgeLink] = {}
        self.knots: Dict[str, KnotNode] = {}
        self.fields: Dict[str, FieldZone] = {}

        self.activation_history: Dict[str, List[float]] = {}
        self.phase_history: Dict[str, List[float]] = {}
        self.sim_running = False
        self.sim_step = 0
        self.max_history = 32
        self.last_runtime: Optional[RuntimeGraphSpec] = None

        self._build_ui()
        self._populate_demo_scene()
        self._refresh_metrics()
        self._log("Ready. Draw agent fields with loops, swirls, knots, and entropy zones.")

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.left.grid(row=0, column=0, sticky="nsew")
        self.left.grid_propagate(False)

        self.center = ctk.CTkFrame(self, corner_radius=0)
        self.center.grid(row=0, column=1, sticky="nsew")
        self.center.grid_columnconfigure(0, weight=1)
        self.center.grid_rowconfigure(0, weight=1)

        self.right = ctk.CTkFrame(self, width=430, corner_radius=0)
        self.right.grid(row=0, column=2, sticky="nsew")
        self.right.grid_propagate(False)

        self._build_left_panel()
        self._build_center_panel()
        self._build_right_panel()
        self.set_mode(ToolMode.SELECT)

    def _build_left_panel(self) -> None:
        ctk.CTkLabel(self.left, text="Resonance Tools", font=ctk.CTkFont(size=24, weight="bold")).pack(
            padx=18, pady=(18, 12), anchor="w"
        )

        self.tool_buttons: Dict[ToolMode, ctk.CTkButton] = {}
        tools = [
            ("Select / Move", ToolMode.SELECT),
            ("Add Agent", ToolMode.AGENT),
            ("Add Artifact", ToolMode.ARTIFACT),
            ("Draw Looptie", ToolMode.LOOPTIE),
            ("Add Swirl", ToolMode.SWIRL),
            ("Add Knot", ToolMode.KNOT),
            ("Draw Field Zone", ToolMode.FIELD),
        ]
        for label, mode in tools:
            btn = ctk.CTkButton(self.left, text=label, command=lambda m=mode: self.set_mode(m))
            btn.pack(fill="x", padx=18, pady=5)
            self.tool_buttons[mode] = btn

        ctk.CTkLabel(self.left, text="Default agent parameters", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=18, pady=(18, 6), anchor="w"
        )
        self.agent_name_var = ctk.StringVar(value="")
        self.agent_role_var = ctk.StringVar(value="generalist")
        self.agent_prompt_var = ctk.StringVar(value="")
        self.agent_phase_var = ctk.DoubleVar(value=0.0)
        self.agent_entropy_var = ctk.DoubleVar(value=0.50)
        self.agent_frequency_var = ctk.DoubleVar(value=0.03)

        ctk.CTkEntry(self.left, textvariable=self.agent_name_var, placeholder_text="Next agent label").pack(
            fill="x", padx=18, pady=5
        )
        ctk.CTkEntry(self.left, textvariable=self.agent_role_var, placeholder_text="Role").pack(
            fill="x", padx=18, pady=5
        )
        ctk.CTkEntry(self.left, textvariable=self.agent_prompt_var, placeholder_text="Prompt seed").pack(
            fill="x", padx=18, pady=5
        )
        ctk.CTkLabel(self.left, text="Initial phase").pack(padx=18, pady=(8, 0), anchor="w")
        ctk.CTkSlider(self.left, from_=-math.pi, to=math.pi, variable=self.agent_phase_var).pack(
            fill="x", padx=18, pady=4
        )
        ctk.CTkLabel(self.left, text="Entropy bias").pack(padx=18, pady=(8, 0), anchor="w")
        ctk.CTkSlider(self.left, from_=0.0, to=1.0, variable=self.agent_entropy_var).pack(
            fill="x", padx=18, pady=4
        )
        ctk.CTkLabel(self.left, text="Natural frequency").pack(padx=18, pady=(8, 0), anchor="w")
        ctk.CTkSlider(self.left, from_=0.0, to=0.12, variable=self.agent_frequency_var).pack(
            fill="x", padx=18, pady=4
        )

        quick_frame = ctk.CTkFrame(self.left)
        quick_frame.pack(fill="x", padx=18, pady=(16, 10))
        quick_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(quick_frame, text="Auto Layout", command=self.auto_layout).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(quick_frame, text="Randomize Phase", command=self.randomize_phases).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(quick_frame, text="Sample Scene", command=self._populate_demo_scene).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(quick_frame, text="Clear", command=self.clear_canvas).grid(row=1, column=1, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(self.left, text="Scene equations", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=18, pady=(12, 6), anchor="w"
        )
        self.equations_box = ctk.CTkTextbox(self.left, height=270, wrap="word")
        self.equations_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.equations_box.insert(
            "end",
            "Activation:\n"
            "a_i(t+1)=tanh(0.55 a_i + 0.35 Σ_j W_ij r_ij a_j(t-τ_ij) + 0.25 A_i + 0.18 S_i - 0.22 P_i + ξ_i)\n\n"
            "Phase:\n"
            "θ_i(t+1)=θ_i + ω_i + K Σ_j W_ij sin(θ_j(t-τ_ij)-θ_i-τ_ij)\n\n"
            "Local entropy:\n"
            "H_i=-Σ_k p_{ik} log_2 p_{ik}\n\n"
            "Creativity band penalty:\n"
            "P_i=max(0,H_min-H_i)+max(0,H_i-H_max)\n\n"
            "Resonance:\n"
            "r_ij=0.5+0.5 cos(θ_i-θ_j-τ_ij)\n"
        )
        self.equations_box.configure(state="disabled")

    def _build_center_panel(self) -> None:
        self.canvas = tk.Canvas(self.center, bg="#101317", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self._draw_grid()

        self.metrics_frame = ctk.CTkFrame(self.center)
        self.metrics_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.metrics_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.metric_labels = {}
        for idx, key in enumerate([
            "Entropy",
            "Resonance",
            "Affinity",
            "Spectral Radius",
            "Creativity Band",
        ]):
            box = ctk.CTkFrame(self.metrics_frame)
            box.grid(row=0, column=idx, padx=4, pady=4, sticky="ew")
            ctk.CTkLabel(box, text=key, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(6, 0))
            label = ctk.CTkLabel(box, text="--", font=ctk.CTkFont(size=16))
            label.pack(pady=(2, 8))
            self.metric_labels[key] = label

    def _build_right_panel(self) -> None:
        tabs = ctk.CTkTabview(self.right)
        tabs.pack(fill="both", expand=True, padx=14, pady=14)
        self.compiler_tab = tabs.add("Compiler")
        self.inspector_tab = tabs.add("Inspector")
        self.sim_tab = tabs.add("Simulation")
        self.output_tab = tabs.add("Output")

        self._build_compiler_tab()
        self._build_inspector_tab()
        self._build_sim_tab()
        self._build_output_tab()

    def _build_compiler_tab(self) -> None:
        self.api_key_var = ctk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
        self.model_var = ctk.StringVar(value="gpt-5.4")
        self.reasoning_var = ctk.StringVar(value="high")
        self.entropy_min_var = ctk.DoubleVar(value=0.25)
        self.entropy_max_var = ctk.DoubleVar(value=0.80)

        ctk.CTkLabel(self.compiler_tab, text="OpenAI compiler", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        ctk.CTkEntry(self.compiler_tab, textvariable=self.api_key_var, show="*", placeholder_text="OPENAI_API_KEY").pack(
            fill="x", padx=12, pady=6
        )
        ctk.CTkEntry(self.compiler_tab, textvariable=self.model_var, placeholder_text="Model").pack(
            fill="x", padx=12, pady=6
        )
        ctk.CTkEntry(self.compiler_tab, textvariable=self.reasoning_var, placeholder_text="Reasoning effort").pack(
            fill="x", padx=12, pady=6
        )
        ctk.CTkLabel(self.compiler_tab, text="Entropy bounds for creativity").pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(self.compiler_tab, text="Lower").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.compiler_tab, from_=0.0, to=1.0, variable=self.entropy_min_var, command=lambda _v: self._refresh_metrics()).pack(
            fill="x", padx=12, pady=4
        )
        ctk.CTkLabel(self.compiler_tab, text="Upper").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.compiler_tab, from_=0.0, to=1.0, variable=self.entropy_max_var, command=lambda _v: self._refresh_metrics()).pack(
            fill="x", padx=12, pady=4
        )

        btn_frame = ctk.CTkFrame(self.compiler_tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=10)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_frame, text="Compile Local", command=self.compile_local).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="Compile with GPT", command=self.compile_with_gpt).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="Export Runtime", command=self.export_runtime_json).grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="Export Python", command=self.export_runtime_python).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="Save Project", command=self.save_project).grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="Load Project", command=self.load_project).grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        self.compiler_summary_box = ctk.CTkTextbox(self.compiler_tab, height=360, wrap="word")
        self.compiler_summary_box.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def _build_inspector_tab(self) -> None:
        ctk.CTkLabel(self.inspector_tab, text="Selection inspector", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        self.inspect_kind_var = ctk.StringVar(value="None")
        self.inspect_id_var = ctk.StringVar(value="")
        self.inspect_name_var = ctk.StringVar(value="")
        self.inspect_role_var = ctk.StringVar(value="")
        self.inspect_text_var = ctk.StringVar(value="")
        self.inspect_phase_var = ctk.DoubleVar(value=0.0)
        self.inspect_entropy_var = ctk.DoubleVar(value=0.5)
        self.inspect_strength_var = ctk.DoubleVar(value=1.0)
        self.inspect_lag_var = ctk.DoubleVar(value=0.0)
        self.inspect_recursion_var = ctk.IntVar(value=0)
        self.inspect_threshold_var = ctk.DoubleVar(value=0.72)

        ctk.CTkLabel(self.inspector_tab, textvariable=self.inspect_kind_var).pack(anchor="w", padx=12)
        ctk.CTkLabel(self.inspector_tab, textvariable=self.inspect_id_var, text_color="#8ba3b4").pack(anchor="w", padx=12, pady=(0, 8))
        ctk.CTkEntry(self.inspector_tab, textvariable=self.inspect_name_var, placeholder_text="Name / label").pack(fill="x", padx=12, pady=5)
        ctk.CTkEntry(self.inspector_tab, textvariable=self.inspect_role_var, placeholder_text="Role / type").pack(fill="x", padx=12, pady=5)
        ctk.CTkEntry(self.inspector_tab, textvariable=self.inspect_text_var, placeholder_text="Prompt / text").pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(self.inspector_tab, text="Phase / lag").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.inspector_tab, from_=-math.pi, to=math.pi, variable=self.inspect_phase_var).pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(self.inspector_tab, text="Entropy / strength / threshold").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.inspector_tab, from_=0.0, to=1.5, variable=self.inspect_entropy_var).pack(fill="x", padx=12, pady=4)
        ctk.CTkSlider(self.inspector_tab, from_=0.0, to=2.0, variable=self.inspect_strength_var).pack(fill="x", padx=12, pady=4)
        ctk.CTkSlider(self.inspector_tab, from_=0.0, to=1.0, variable=self.inspect_threshold_var).pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(self.inspector_tab, text="Swirl recursion").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.inspector_tab, from_=0, to=6, number_of_steps=6, variable=self.inspect_recursion_var).pack(fill="x", padx=12, pady=4)

        control_frame = ctk.CTkFrame(self.inspector_tab, fg_color="transparent")
        control_frame.pack(fill="x", padx=12, pady=10)
        control_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(control_frame, text="Apply", command=self.apply_selection_changes).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(control_frame, text="Delete", command=self.delete_selection).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        self.inspector_box = ctk.CTkTextbox(self.inspector_tab, height=360, wrap="word")
        self.inspector_box.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def _build_sim_tab(self) -> None:
        ctk.CTkLabel(self.sim_tab, text="Phase-lag simulation", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        self.sim_steps_var = ctk.IntVar(value=1)
        self.sim_gain_var = ctk.DoubleVar(value=0.72)
        ctk.CTkLabel(self.sim_tab, text="Steps per run").pack(anchor="w", padx=12)
        ctk.CTkSlider(self.sim_tab, from_=1, to=25, number_of_steps=24, variable=self.sim_steps_var).pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(self.sim_tab, text="Coupling gain K").pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkSlider(self.sim_tab, from_=0.1, to=1.5, variable=self.sim_gain_var).pack(fill="x", padx=12, pady=4)

        sim_btns = ctk.CTkFrame(self.sim_tab, fg_color="transparent")
        sim_btns.pack(fill="x", padx=12, pady=10)
        sim_btns.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(sim_btns, text="Step", command=lambda: self.simulate_steps(self.sim_steps_var.get())).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(sim_btns, text="Run / Pause", command=self.toggle_simulation).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(sim_btns, text="Reset", command=self.reset_simulation).grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        self.sim_status_var = ctk.StringVar(value="step=0")
        ctk.CTkLabel(self.sim_tab, textvariable=self.sim_status_var, text_color="#9bb4c7").pack(anchor="w", padx=12)
        self.sim_trace_box = ctk.CTkTextbox(self.sim_tab, height=420, wrap="word")
        self.sim_trace_box.pack(fill="both", expand=True, padx=12, pady=(8, 12))

    def _build_output_tab(self) -> None:
        ctk.CTkLabel(self.output_tab, text="Compiled runtime", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        self.output_box = ctk.CTkTextbox(self.output_tab, height=380, wrap="word")
        self.output_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        ctk.CTkLabel(self.output_tab, text="Log", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 4)
        )
        self.log_box = ctk.CTkTextbox(self.output_tab, height=280, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    def _draw_grid(self) -> None:
        for x in range(0, 2200, 40):
            self.canvas.create_line(x, 0, x, 1600, fill="#182028")
        for y in range(0, 1600, 40):
            self.canvas.create_line(0, y, 2200, y, fill="#182028")

    def _field_color(self, theme: str) -> Tuple[str, str]:
        palette = {
            "studio": ("#123046", "#2dd4bf"),
            "deploy": ("#1f3a18", "#4ade80"),
            "critique": ("#3f1d2e", "#fb7185"),
            "research": ("#221b4d", "#a78bfa"),
        }
        return palette.get(theme, ("#123046", "#2dd4bf"))

    def _agent_color(self, entropy_bias: float, coherence: float) -> Tuple[str, str]:
        if entropy_bias < 0.33:
            base = "#3b82f6"
        elif entropy_bias < 0.66:
            base = "#8b5cf6"
        else:
            base = "#f97316"
        halo = "#ecfeff" if coherence > 0.72 else "#94a3b8"
        return base, halo

    def _draw_field(self, zone: FieldZone) -> None:
        fill, outline = self._field_color(zone.theme)
        x1, y1, x2, y2 = zone.x1, zone.y1, zone.x2, zone.y2
        rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=fill,
            outline=outline,
            width=2,
            dash=(6, 4),
            stipple="gray25",
        )
        label = self.canvas.create_text(
            (x1 + x2) / 2,
            y1 + 14,
            text=f"{zone.label} [{zone.entropy_min:.2f}, {zone.entropy_max:.2f}]",
            fill=outline,
            font=("Arial", 10, "bold"),
        )
        zone.canvas_items = [rect, label]
        for item in zone.canvas_items:
            self.canvas_to_model[item] = ("field", zone.zone_id)
        self.canvas.tag_lower(rect)

    def _draw_agent(self, agent: AgentNode) -> None:
        x, y, r = agent.x, agent.y, self.AGENT_RADIUS
        base, halo = self._agent_color(agent.entropy_bias, agent.coherence)
        outer_r = r + 10 + int(agent.halo_strength * 12)
        ring = self.canvas.create_oval(x - outer_r, y - outer_r, x + outer_r, y + outer_r, outline=halo, width=2)
        body = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=base, outline="#e2e8f0", width=2)
        act = self.canvas.create_text(x, y - 2, text=agent.name, fill="white", width=110, font=("Arial", 10, "bold"))
        sub = self.canvas.create_text(
            x,
            y + 42,
            text=f"{agent.role} · a={agent.activation:+.2f}",
            fill="#d0d9df",
            font=("Arial", 9),
        )
        phase_tick = self.canvas.create_line(
            x,
            y,
            x + math.cos(agent.phase) * (r + 12),
            y + math.sin(agent.phase) * (r + 12),
            fill="#fef3c7",
            width=3,
        )
        agent.canvas_items = [ring, body, act, sub, phase_tick]
        for item in agent.canvas_items:
            self.canvas_to_model[item] = ("agent", agent.node_id)

    def _draw_swirl(self, agent: AgentNode) -> None:
        for idx in range(agent.recursion_depth):
            pad = 12 + idx * 7
            arc = self.canvas.create_arc(
                agent.x - self.AGENT_RADIUS - pad,
                agent.y - self.AGENT_RADIUS - pad,
                agent.x + self.AGENT_RADIUS + pad,
                agent.y + self.AGENT_RADIUS + pad,
                start=25 + idx * 14,
                extent=285,
                style=tk.ARC,
                outline="#f472b6",
                width=2,
            )
            tip = self.canvas.create_line(
                agent.x + self.AGENT_RADIUS + pad - 8,
                agent.y - 4,
                agent.x + self.AGENT_RADIUS + pad + 6,
                agent.y - 10,
                fill="#f472b6",
                width=2,
            )
            agent.canvas_items.extend([arc, tip])
            self.canvas_to_model[arc] = ("agent", agent.node_id)
            self.canvas_to_model[tip] = ("agent", agent.node_id)

    def _draw_artifact(self, artifact: ArtifactNode) -> None:
        x, y, w, h = artifact.x, artifact.y, self.ARTIFACT_W, self.ARTIFACT_H
        rect = self.canvas.create_rectangle(
            x - w / 2, y - h / 2, x + w / 2, y + h / 2,
            fill="#1f2937", outline="#facc15", width=2
        )
        tag = self.canvas.create_text(
            x,
            y - 20,
            text=f"{artifact.kind} · w={artifact.weight:.2f}",
            fill="#fcd34d",
            font=("Arial", 9, "bold"),
        )
        text = self.canvas.create_text(
            x,
            y + 6,
            text=artifact.text,
            fill="#fde68a",
            width=w - 16,
            font=("Arial", 10),
        )
        artifact.canvas_items = [rect, tag, text]
        for item in artifact.canvas_items:
            self.canvas_to_model[item] = ("artifact", artifact.artifact_id)

    def _draw_looptie(self, edge: EdgeLink) -> None:
        if edge.source_id not in self.agents or edge.target_id not in self.agents:
            return
        a = self.agents[edge.source_id]
        b = self.agents[edge.target_id]
        dx = b.x - a.x
        dy = b.y - a.y
        dist = max(math.hypot(dx, dy), 1.0)
        nx, ny = -dy / dist, dx / dist
        cx = (a.x + b.x) / 2 + nx * edge.curve
        cy = (a.y + b.y) / 2 + ny * edge.curve
        resonance = self._phase_resonance(a, b, edge.phase_lag)
        if resonance < 0.33:
            color = "#60a5fa"
        elif resonance < 0.66:
            color = "#7dd3fc"
        else:
            color = "#f472b6"
        width = max(2, int(2 + edge.tie_strength * 2.4))
        line = self.canvas.create_line(
            a.x,
            a.y,
            cx,
            cy,
            b.x,
            b.y,
            smooth=True,
            splinesteps=32,
            fill=color,
            width=width,
        )
        label = self.canvas.create_text(
            cx,
            cy - 16,
            text=f"τ={edge.phase_lag:.2f} · r={resonance:.2f}",
            fill="#bae6fd",
            font=("Arial", 9),
        )
        edge.canvas_items = [line, label]
        for item in edge.canvas_items:
            self.canvas_to_model[item] = ("edge", edge.edge_id)
            self.canvas.tag_lower(line)

    def _draw_knot(self, knot: KnotNode) -> None:
        x, y, r = knot.x, knot.y, self.KNOT_RADIUS
        body = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#22c55e", outline="#dcfce7", width=2)
        c1 = self.canvas.create_line(x - r, y - r, x + r, y + r, fill="#dcfce7", width=2)
        c2 = self.canvas.create_line(x - r, y + r, x + r, y - r, fill="#dcfce7", width=2)
        tag = self.canvas.create_text(x, y + 22, text=f"q={knot.quorum}", fill="#bbf7d0", font=("Arial", 9))
        knot.canvas_items = [body, c1, c2, tag]
        for item in knot.canvas_items:
            self.canvas_to_model[item] = ("knot", knot.knot_id)
        for agent_id in knot.attached_agent_ids:
            if agent_id in self.agents:
                a = self.agents[agent_id]
                line = self.canvas.create_line(x, y, a.x, a.y, dash=(3, 5), fill="#4ade80", width=2)
                self.canvas_to_model[line] = ("knot", knot.knot_id)
                self.canvas.tag_lower(line)
                knot.canvas_items.append(line)

    def redraw_scene(self) -> None:
        self.canvas.delete("all")
        self.canvas_to_model.clear()
        self._draw_grid()
        for zone in self.fields.values():
            zone.canvas_items = []
            self._draw_field(zone)
        for edge in self.edges.values():
            edge.canvas_items = []
            self._draw_looptie(edge)
        for artifact in self.artifacts.values():
            artifact.canvas_items = []
            self._draw_artifact(artifact)
        for agent in self.agents.values():
            agent.canvas_items = []
            self._draw_agent(agent)
        for agent in self.agents.values():
            if agent.recursion_depth > 0:
                self._draw_swirl(agent)
        for knot in self.knots.values():
            knot.canvas_items = []
            self._draw_knot(knot)
        self._highlight_selection()
        self._refresh_metrics()

    def _highlight_selection(self) -> None:
        if not self.selected:
            return
        kind, obj_id = self.selected
        mapping = {
            "agent": self.agents,
            "artifact": self.artifacts,
            "edge": self.edges,
            "knot": self.knots,
            "field": self.fields,
        }
        obj = mapping.get(kind, {}).get(obj_id)
        if not obj:
            return
        for item in getattr(obj, "canvas_items", [])[:1]:
            try:
                self.canvas.itemconfigure(item, width=4)
            except tk.TclError:
                pass

    # --------------------------------------------------------
    # Logging and utility
    # --------------------------------------------------------

    def _log(self, msg: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")

    def _write_output(self, text: str) -> None:
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", text)

    def set_mode(self, mode: ToolMode) -> None:
        self.mode = mode
        for m, btn in self.tool_buttons.items():
            btn.configure(fg_color="#1f6aa5" if m == mode else "#3b8ed0")
        self.pending_link_start = None
        self.pending_field_start = None
        self._log(f"Mode: {mode.value}")

    def _new_agent_name(self) -> str:
        label = self.agent_name_var.get().strip() or f"Agent {self.agent_counter}"
        self.agent_counter += 1
        return label

    def _simple_input(self, title: str, default: str = "") -> Optional[str]:
        dialog = ctk.CTkInputDialog(text=title, title=title)
        value = dialog.get_input()
        if value is None:
            return default if default else None
        value = value.strip()
        return value or default

    def _find_current_hit(self) -> Optional[Tuple[str, str]]:
        current = self.canvas.find_withtag("current")
        if not current:
            return None
        item_id = current[0]
        return self.canvas_to_model.get(item_id)

    def _nearest_entity(self, x: float, y: float, kinds: Tuple[str, ...] = ("agent", "artifact", "knot", "field")) -> Optional[Tuple[str, str]]:
        best: Optional[Tuple[str, str]] = None
        best_d = 1e9
        for kind in kinds:
            mapping = {
                "agent": self.agents,
                "artifact": self.artifacts,
                "knot": self.knots,
                "field": self.fields,
            }.get(kind, {})
            for obj_id, obj in mapping.items():
                if kind == "field":
                    cx = (obj.x1 + obj.x2) / 2
                    cy = (obj.y1 + obj.y2) / 2
                else:
                    cx = obj.x
                    cy = obj.y
                d = math.dist((x, y), (cx, cy))
                if d < best_d:
                    best = (kind, obj_id)
                    best_d = d
        return best if best_d < 120 else None

    # --------------------------------------------------------
    # Event handlers
    # --------------------------------------------------------

    def on_canvas_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        hit = self._find_current_hit()

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
                self._log(f"Looptie start = {target[1]}")
            else:
                if self.pending_link_start != target[1]:
                    self.add_looptie(self.pending_link_start, target[1])
                self.pending_link_start = None
            return
        if self.mode == ToolMode.FIELD:
            if self.pending_field_start is None:
                self.pending_field_start = (x, y)
                self._log("Field start placed. Click second corner.")
            else:
                x1, y1 = self.pending_field_start
                self.add_field(x1, y1, x, y)
                self.pending_field_start = None
            return

        if hit:
            self.selected = hit
            self.dragging_ref = hit
            kind, obj_id = hit
            if kind == "field":
                zone = self.fields[obj_id]
                cx = (zone.x1 + zone.x2) / 2
                cy = (zone.y1 + zone.y2) / 2
                self.drag_offset = (cx - x, cy - y)
            else:
                obj = {"agent": self.agents, "artifact": self.artifacts, "knot": self.knots}.get(kind, {}).get(obj_id)
                if obj:
                    self.drag_offset = (obj.x - x, obj.y - y)
                else:
                    self.dragging_ref = None
            self._load_selection_into_inspector()
        else:
            self.selected = None
            self.dragging_ref = None
            self._load_selection_into_inspector()
        self.redraw_scene()

    def on_canvas_drag(self, event) -> None:
        if self.mode != ToolMode.SELECT or not self.dragging_ref:
            return
        kind, obj_id = self.dragging_ref
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if kind == "agent" and obj_id in self.agents:
            a = self.agents[obj_id]
            a.x = x + self.drag_offset[0]
            a.y = y + self.drag_offset[1]
        elif kind == "artifact" and obj_id in self.artifacts:
            art = self.artifacts[obj_id]
            art.x = x + self.drag_offset[0]
            art.y = y + self.drag_offset[1]
        elif kind == "knot" and obj_id in self.knots:
            knot = self.knots[obj_id]
            knot.x = x + self.drag_offset[0]
            knot.y = y + self.drag_offset[1]
            knot.attached_agent_ids = self._agents_near_point(knot.x, knot.y, radius=200)
            knot.quorum = max(2, min(len(knot.attached_agent_ids), knot.quorum)) if knot.attached_agent_ids else 1
        elif kind == "field" and obj_id in self.fields:
            zone = self.fields[obj_id]
            width = zone.x2 - zone.x1
            height = zone.y2 - zone.y1
            cx = x + self.drag_offset[0]
            cy = y + self.drag_offset[1]
            zone.x1 = cx - width / 2
            zone.x2 = cx + width / 2
            zone.y1 = cy - height / 2
            zone.y2 = cy + height / 2
        self.redraw_scene()

    def on_canvas_release(self, _event) -> None:
        self.dragging_ref = None

    def on_canvas_double_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        target = self._nearest_entity(x, y)
        if not target:
            return
        kind, obj_id = target
        if kind == "agent":
            value = self._simple_input("Agent label", self.agents[obj_id].name)
            if value:
                self.agents[obj_id].name = value
        elif kind == "artifact":
            value = self._simple_input("Artifact text", self.artifacts[obj_id].text)
            if value:
                self.artifacts[obj_id].text = value
        elif kind == "field":
            value = self._simple_input("Field label", self.fields[obj_id].label)
            if value:
                self.fields[obj_id].label = value
        self.redraw_scene()

    # --------------------------------------------------------
    # CRUD
    # --------------------------------------------------------

    def add_agent(self, x: float, y: float) -> None:
        node_id = f"agent_{self.agent_counter}"
        agent = AgentNode(
            node_id=node_id,
            name=self._new_agent_name(),
            x=x,
            y=y,
            role=self.agent_role_var.get().strip() or "generalist",
            prompt_seed=self.agent_prompt_var.get().strip(),
            phase=float(self.agent_phase_var.get()),
            frequency=float(self.agent_frequency_var.get()),
            entropy_bias=float(self.agent_entropy_var.get()),
            halo_strength=0.55,
        )
        if "deploy" in agent.role.lower():
            agent.allowed_tools.append("deploy")
        if "critic" in agent.role.lower() or "verify" in agent.role.lower():
            agent.allowed_tools.append("judge")
        self.agents[node_id] = agent
        self.activation_history[node_id] = [0.0]
        self.phase_history[node_id] = [agent.phase]
        self.redraw_scene()
        self._log(f"Added agent {node_id} ({agent.role})")

    def add_artifact(self, x: float, y: float) -> None:
        artifact_id = f"artifact_{self.artifact_counter}"
        self.artifact_counter += 1
        text = self._simple_input("Artifact prompt", "idea, image cue, or note") or "untitled artifact"
        artifact = ArtifactNode(artifact_id=artifact_id, text=text, x=x, y=y, weight=1.0)
        self.artifacts[artifact_id] = artifact
        self.redraw_scene()
        self._log(f"Added artifact {artifact_id}")

    def add_looptie(self, source_id: str, target_id: str) -> None:
        if source_id not in self.agents or target_id not in self.agents:
            return
        edge_id = f"edge_{self.edge_counter}"
        self.edge_counter += 1
        a = self.agents[source_id]
        b = self.agents[target_id]
        dist = max(120.0, math.dist((a.x, a.y), (b.x, b.y)))
        edge = EdgeLink(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            tie_strength=max(0.3, min(1.7, 230.0 / dist)),
            phase_lag=random.uniform(-1.3, 1.3),
            curve=random.choice([34.0, 48.0, 62.0, -36.0, -54.0, -70.0]),
            bandwidth=random.uniform(0.6, 1.4),
            recurrence=random.uniform(0.35, 0.95),
        )
        self.edges[edge_id] = edge
        self.redraw_scene()
        self._log(f"Added looptie {edge_id}: {source_id} -> {target_id}")

    def add_swirl(self, agent_id: str) -> None:
        if agent_id not in self.agents:
            return
        self.agents[agent_id].recursion_depth += 1
        self.redraw_scene()
        self._log(f"Swirl recursion on {agent_id} = {self.agents[agent_id].recursion_depth}")

    def add_knot(self, x: float, y: float) -> None:
        knot_id = f"knot_{self.knot_counter}"
        self.knot_counter += 1
        attached = self._agents_near_point(x, y, radius=190)
        knot = KnotNode(
            knot_id=knot_id,
            x=x,
            y=y,
            sync_threshold=0.72,
            quorum=max(2, min(3, len(attached))) if attached else 1,
            attached_agent_ids=attached,
        )
        self.knots[knot_id] = knot
        self.redraw_scene()
        self._log(f"Added knot {knot_id} with {len(attached)} attached agents")

    def add_field(self, x1: float, y1: float, x2: float, y2: float) -> None:
        zone_id = f"zone_{self.zone_counter}"
        self.zone_counter += 1
        label = self._simple_input("Field label", f"field_{self.zone_counter}") or f"field_{self.zone_counter}"
        zone = FieldZone(
            zone_id=zone_id,
            label=label,
            x1=min(x1, x2),
            y1=min(y1, y2),
            x2=max(x1, x2),
            y2=max(y1, y2),
            entropy_min=float(self.entropy_min_var.get()),
            entropy_max=float(self.entropy_max_var.get()),
            theme=random.choice(["studio", "critique", "research", "deploy"]),
        )
        self.fields[zone_id] = zone
        self.redraw_scene()
        self._log(f"Added field zone {zone_id}")

    def delete_selection(self) -> None:
        if not self.selected:
            return
        kind, obj_id = self.selected
        if kind == "agent":
            self.agents.pop(obj_id, None)
            self.activation_history.pop(obj_id, None)
            self.phase_history.pop(obj_id, None)
            self.edges = {eid: e for eid, e in self.edges.items() if e.source_id != obj_id and e.target_id != obj_id}
            for knot in self.knots.values():
                if obj_id in knot.attached_agent_ids:
                    knot.attached_agent_ids.remove(obj_id)
        elif kind == "artifact":
            self.artifacts.pop(obj_id, None)
        elif kind == "edge":
            self.edges.pop(obj_id, None)
        elif kind == "knot":
            self.knots.pop(obj_id, None)
        elif kind == "field":
            self.fields.pop(obj_id, None)
        self.selected = None
        self.redraw_scene()
        self._load_selection_into_inspector()
        self._log(f"Deleted {kind}:{obj_id}")

    def clear_canvas(self) -> None:
        self.agents.clear()
        self.artifacts.clear()
        self.edges.clear()
        self.knots.clear()
        self.fields.clear()
        self.activation_history.clear()
        self.phase_history.clear()
        self.selected = None
        self.sim_running = False
        self.sim_step = 0
        self.redraw_scene()
        self._load_selection_into_inspector()
        self.output_box.delete("1.0", "end")
        self.compiler_summary_box.delete("1.0", "end")
        self.sim_trace_box.delete("1.0", "end")
        self._log("Canvas cleared")

    # --------------------------------------------------------
    # Inspector
    # --------------------------------------------------------

    def _load_selection_into_inspector(self) -> None:
        self.inspector_box.delete("1.0", "end")
        if not self.selected:
            self.inspect_kind_var.set("None")
            self.inspect_id_var.set("")
            self.inspect_name_var.set("")
            self.inspect_role_var.set("")
            self.inspect_text_var.set("")
            return

        kind, obj_id = self.selected
        self.inspect_kind_var.set(kind.title())
        self.inspect_id_var.set(obj_id)
        if kind == "agent":
            a = self.agents[obj_id]
            self.inspect_name_var.set(a.name)
            self.inspect_role_var.set(a.role)
            self.inspect_text_var.set(a.prompt_seed)
            self.inspect_phase_var.set(a.phase)
            self.inspect_entropy_var.set(a.entropy_bias)
            self.inspect_strength_var.set(a.halo_strength)
            self.inspect_recursion_var.set(a.recursion_depth)
            payload = {
                "activation": round(a.activation, 3),
                "coherence": round(a.coherence, 3),
                "fields": self._field_membership_for_point(a.x, a.y),
                "prompt_artifacts": self._artifact_prompts_for_agent(a),
                "tools": a.allowed_tools,
            }
        elif kind == "artifact":
            art = self.artifacts[obj_id]
            self.inspect_name_var.set(art.artifact_id)
            self.inspect_role_var.set(art.kind)
            self.inspect_text_var.set(art.text)
            self.inspect_phase_var.set(0.0)
            self.inspect_entropy_var.set(art.weight)
            self.inspect_strength_var.set(art.weight)
            payload = {"prompt_mode": art.prompt_mode, "weight": art.weight}
        elif kind == "edge":
            e = self.edges[obj_id]
            self.inspect_name_var.set(e.edge_id)
            self.inspect_role_var.set(e.interaction)
            self.inspect_text_var.set(f"{e.source_id} -> {e.target_id}")
            self.inspect_phase_var.set(e.phase_lag)
            self.inspect_entropy_var.set(e.recurrence)
            self.inspect_strength_var.set(e.tie_strength)
            payload = {
                "bandwidth": e.bandwidth,
                "curve": e.curve,
                "resonance": round(self._phase_resonance(self.agents[e.source_id], self.agents[e.target_id], e.phase_lag), 3),
            }
        elif kind == "knot":
            k = self.knots[obj_id]
            self.inspect_name_var.set(k.knot_id)
            self.inspect_role_var.set("knot")
            self.inspect_text_var.set(", ".join(k.attached_agent_ids))
            self.inspect_threshold_var.set(k.sync_threshold)
            self.inspect_strength_var.set(k.quorum)
            payload = {"agents": k.attached_agent_ids, "quorum": k.quorum}
        else:
            z = self.fields[obj_id]
            self.inspect_name_var.set(z.label)
            self.inspect_role_var.set(z.theme)
            self.inspect_text_var.set(f"{z.x1:.0f},{z.y1:.0f} -> {z.x2:.0f},{z.y2:.0f}")
            self.inspect_entropy_var.set(z.entropy_min)
            self.inspect_strength_var.set(z.entropy_max)
            payload = {"band": [z.entropy_min, z.entropy_max], "theme": z.theme}
        self.inspector_box.insert("end", json.dumps(payload, indent=2))

    def apply_selection_changes(self) -> None:
        if not self.selected:
            return
        kind, obj_id = self.selected
        if kind == "agent" and obj_id in self.agents:
            a = self.agents[obj_id]
            a.name = self.inspect_name_var.get().strip() or a.name
            a.role = self.inspect_role_var.get().strip() or a.role
            a.prompt_seed = self.inspect_text_var.get().strip()
            a.phase = float(self.inspect_phase_var.get())
            a.entropy_bias = max(0.0, min(1.0, float(self.inspect_entropy_var.get())))
            a.halo_strength = max(0.0, min(1.5, float(self.inspect_strength_var.get())))
            a.recursion_depth = max(0, int(round(float(self.inspect_recursion_var.get()))))
        elif kind == "artifact" and obj_id in self.artifacts:
            art = self.artifacts[obj_id]
            art.kind = self.inspect_role_var.get().strip() or art.kind
            art.text = self.inspect_text_var.get().strip() or art.text
            art.weight = max(0.1, min(2.0, float(self.inspect_strength_var.get())))
        elif kind == "edge" and obj_id in self.edges:
            e = self.edges[obj_id]
            e.interaction = self.inspect_role_var.get().strip() or e.interaction
            e.phase_lag = float(self.inspect_phase_var.get())
            e.recurrence = max(0.0, min(1.5, float(self.inspect_entropy_var.get())))
            e.tie_strength = max(0.1, min(2.0, float(self.inspect_strength_var.get())))
        elif kind == "knot" and obj_id in self.knots:
            k = self.knots[obj_id]
            k.sync_threshold = max(0.0, min(1.0, float(self.inspect_threshold_var.get())))
            k.quorum = max(1, int(round(float(self.inspect_strength_var.get()))))
        elif kind == "field" and obj_id in self.fields:
            z = self.fields[obj_id]
            z.label = self.inspect_name_var.get().strip() or z.label
            z.theme = self.inspect_role_var.get().strip() or z.theme
            z.entropy_min = max(0.0, min(1.0, float(self.inspect_entropy_var.get())))
            z.entropy_max = max(z.entropy_min, min(1.0, float(self.inspect_strength_var.get())))
        self.redraw_scene()
        self._load_selection_into_inspector()
        self._log(f"Updated {kind}:{obj_id}")

    # --------------------------------------------------------
    # Semantics and metrics
    # --------------------------------------------------------

    def _agents_near_point(self, x: float, y: float, radius: float) -> List[str]:
        return [aid for aid, a in self.agents.items() if math.dist((x, y), (a.x, a.y)) <= radius]

    def _field_membership_for_point(self, x: float, y: float) -> List[str]:
        members = []
        for zone in self.fields.values():
            if zone.x1 <= x <= zone.x2 and zone.y1 <= y <= zone.y2:
                members.append(zone.zone_id)
        return members

    def _field_targets_for_agent(self, agent: AgentNode) -> Tuple[float, float]:
        members = [self.fields[zid] for zid in self._field_membership_for_point(agent.x, agent.y) if zid in self.fields]
        if not members:
            return float(self.entropy_min_var.get()), float(self.entropy_max_var.get())
        emin = sum(z.entropy_min for z in members) / len(members)
        emax = sum(z.entropy_max for z in members) / len(members)
        return emin, emax

    def _distance_affinity(self, a: AgentNode, b: AgentNode, sigma: float = 230.0) -> float:
        d = math.dist((a.x, a.y), (b.x, b.y))
        return math.exp(-(d ** 2) / (2 * sigma ** 2))

    def _phase_resonance(self, a: AgentNode, b: AgentNode, lag: float) -> float:
        return 0.5 + 0.5 * math.cos(a.phase - b.phase - lag)

    def _artifact_drive_for_agent(self, agent: AgentNode, radius: float = 240.0) -> float:
        drive = 0.0
        for art in self.artifacts.values():
            d = math.dist((agent.x, agent.y), (art.x, art.y))
            if d <= radius:
                drive += art.weight * math.exp(-(d ** 2) / (2 * (radius / 1.7) ** 2))
        return drive

    def _artifact_prompts_for_agent(self, agent: AgentNode, radius: float = 240.0) -> List[str]:
        prompts = []
        for art in self.artifacts.values():
            d = math.dist((agent.x, agent.y), (art.x, art.y))
            if d <= radius:
                prompts.append(f"[{art.weight:.2f}] {art.text}")
        return prompts

    def _edge_resonance(self, edge: EdgeLink) -> float:
        if edge.source_id not in self.agents or edge.target_id not in self.agents:
            return 0.0
        return self._phase_resonance(self.agents[edge.source_id], self.agents[edge.target_id], edge.phase_lag)

    def _local_entropy(self, agent_id: str) -> float:
        if agent_id not in self.agents:
            return 0.0
        agent = self.agents[agent_id]
        masses = [1.0]
        masses.extend(
            e.tie_strength * max(0.2, e.recurrence)
            for e in self.edges.values()
            if e.source_id == agent_id or e.target_id == agent_id
        )
        masses.extend(0.6 for knot in self.knots.values() if agent_id in knot.attached_agent_ids)
        masses.extend(
            0.8 * art.weight
            for art in self.artifacts.values()
            if math.dist((agent.x, agent.y), (art.x, art.y)) <= 240
        )
        members = self._field_membership_for_point(agent.x, agent.y)
        masses.extend(0.5 for _ in members)
        total = sum(masses)
        if total <= 0:
            return 0.0
        probs = [m / total for m in masses if m > 0]
        raw = -sum(p * math.log(max(p, 1e-9), 2) for p in probs)
        return raw / max(1.0, math.log(len(probs) + 1, 2))

    def _human_organized_entropy(self) -> float:
        if not self.agents:
            return 0.0
        return sum(self._local_entropy(aid) for aid in self.agents) / len(self.agents)

    def _spatial_semantics(self) -> Dict[str, float]:
        if len(self.agents) < 2:
            return {"mean_affinity": 0.0, "mean_resonance": 0.0, "mean_activation": 0.0}
        affinities: List[float] = []
        resonances: List[float] = []
        activations: List[float] = []
        if self.edges:
            for edge in self.edges.values():
                if edge.source_id in self.agents and edge.target_id in self.agents:
                    a = self.agents[edge.source_id]
                    b = self.agents[edge.target_id]
                    affinities.append(self._distance_affinity(a, b))
                    resonances.append(self._phase_resonance(a, b, edge.phase_lag))
        else:
            ids = list(self.agents.keys())
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a = self.agents[ids[i]]
                    b = self.agents[ids[j]]
                    affinities.append(self._distance_affinity(a, b))
                    resonances.append(self._phase_resonance(a, b, 0.0))
        activations = [abs(a.activation) for a in self.agents.values()]
        return {
            "mean_affinity": sum(affinities) / max(1, len(affinities)),
            "mean_resonance": sum(resonances) / max(1, len(resonances)),
            "mean_activation": sum(activations) / max(1, len(activations)),
        }

    def _adjacency_spectral_radius(self) -> float:
        ids = list(self.agents.keys())
        n = len(ids)
        if n == 0:
            return 0.0
        index = {aid: i for i, aid in enumerate(ids)}
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for edge in self.edges.values():
            if edge.source_id in index and edge.target_id in index:
                i = index[edge.source_id]
                j = index[edge.target_id]
                r = self._edge_resonance(edge)
                w = edge.tie_strength * edge.bandwidth * (0.4 + 0.6 * r)
                matrix[i][j] += w
                matrix[j][i] += 0.5 * w
        vec = [1.0 / n for _ in range(n)]
        for _ in range(12):
            nxt = [sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(v * v for v in nxt)) or 1.0
            vec = [v / norm for v in nxt]
        num = sum(vec[i] * sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n))
        den = sum(v * v for v in vec) or 1.0
        return num / den

    def _creativity_band_status(self) -> str:
        entropy = self._human_organized_entropy()
        e_min = float(self.entropy_min_var.get())
        e_max = float(self.entropy_max_var.get())
        if entropy < e_min:
            return "too ordered"
        if entropy > e_max:
            return "too noisy"
        return "productive"

    def _refresh_metrics(self) -> None:
        entropy = self._human_organized_entropy()
        semantics = self._spatial_semantics()
        radius = self._adjacency_spectral_radius()
        band = self._creativity_band_status()
        self.metric_labels["Entropy"].configure(text=f"{entropy:.3f}")
        self.metric_labels["Resonance"].configure(text=f"{semantics['mean_resonance']:.3f}")
        self.metric_labels["Affinity"].configure(text=f"{semantics['mean_affinity']:.3f}")
        self.metric_labels["Spectral Radius"].configure(text=f"{radius:.3f}")
        self.metric_labels["Creativity Band"].configure(text=band)

    # --------------------------------------------------------
    # Simulation
    # --------------------------------------------------------

    def reset_simulation(self) -> None:
        self.sim_running = False
        self.sim_step = 0
        for aid, agent in self.agents.items():
            agent.activation = 0.0
            agent.coherence = 0.50
            agent.halo_strength = 0.55
            self.activation_history[aid] = [0.0]
            self.phase_history[aid] = [agent.phase]
        self.sim_trace_box.delete("1.0", "end")
        self.sim_status_var.set("step=0")
        self.redraw_scene()
        self._log("Simulation reset")

    def toggle_simulation(self) -> None:
        self.sim_running = not self.sim_running
        if self.sim_running:
            self._log("Simulation running")
            self._run_sim_loop()
        else:
            self._log("Simulation paused")

    def _run_sim_loop(self) -> None:
        if not self.sim_running:
            return
        self.simulate_steps(self.sim_steps_var.get())
        self.after(260, self._run_sim_loop)

    def _history_value(self, history: List[float], lag_steps: int) -> float:
        idx = max(0, len(history) - 1 - lag_steps)
        return history[idx]

    def simulate_steps(self, steps: int = 1) -> None:
        if not self.agents:
            return
        for _ in range(max(1, steps)):
            gain = float(self.sim_gain_var.get())
            new_activation: Dict[str, float] = {}
            new_phase: Dict[str, float] = {}
            new_coherence: Dict[str, float] = {}

            for aid, agent in self.agents.items():
                neighbor_drive = 0.0
                sync_drive = 0.0
                for edge in self.edges.values():
                    if edge.source_id == aid and edge.target_id in self.agents:
                        other = self.agents[edge.target_id]
                        other_id = other.node_id
                        lag_steps = min(8, max(0, int(round(abs(edge.phase_lag) * 2.5))))
                        delayed_a = self._history_value(self.activation_history.get(other_id, [0.0]), lag_steps)
                        delayed_p = self._history_value(self.phase_history.get(other_id, [other.phase]), lag_steps)
                        resonance = 0.5 + 0.5 * math.cos(agent.phase - delayed_p - edge.phase_lag)
                        neighbor_drive += edge.tie_strength * edge.bandwidth * (0.4 + 0.6 * resonance) * delayed_a
                        sync_drive += edge.tie_strength * math.sin(delayed_p - agent.phase - edge.phase_lag)
                    elif edge.target_id == aid and edge.source_id in self.agents:
                        other = self.agents[edge.source_id]
                        other_id = other.node_id
                        lag_steps = min(8, max(0, int(round(abs(edge.phase_lag) * 2.5))))
                        delayed_a = self._history_value(self.activation_history.get(other_id, [0.0]), lag_steps)
                        delayed_p = self._history_value(self.phase_history.get(other_id, [other.phase]), lag_steps)
                        resonance = 0.5 + 0.5 * math.cos(agent.phase - delayed_p + edge.phase_lag)
                        neighbor_drive += 0.5 * edge.tie_strength * (0.4 + 0.6 * resonance) * delayed_a
                        sync_drive += 0.5 * edge.tie_strength * math.sin(delayed_p - agent.phase + edge.phase_lag)

                artifact_drive = self._artifact_drive_for_agent(agent)
                local_entropy = self._local_entropy(aid)
                h_min, h_max = self._field_targets_for_agent(agent)
                penalty = max(0.0, h_min - local_entropy) + max(0.0, local_entropy - h_max)
                swirl_drive = 0.18 * agent.recursion_depth
                knot_support = 0.0
                for knot in self.knots.values():
                    if aid in knot.attached_agent_ids:
                        support_count = 0
                        for other_id in knot.attached_agent_ids:
                            if other_id == aid or other_id not in self.agents:
                                continue
                            other = self.agents[other_id]
                            support_count += int(other.coherence >= knot.sync_threshold)
                        if support_count >= max(0, knot.quorum - 1):
                            knot_support += 0.18
                noise = random.uniform(-0.05, 0.05)

                act = math.tanh(
                    0.55 * agent.activation
                    + 0.35 * neighbor_drive
                    + 0.25 * artifact_drive
                    + swirl_drive
                    + knot_support
                    - 0.22 * penalty
                    + noise
                )
                phase = agent.phase + agent.frequency + gain * 0.18 * sync_drive
                coherence = max(
                    0.0,
                    min(
                        1.0,
                        0.70 * agent.coherence + 0.20 * (0.5 + 0.5 * math.tanh(neighbor_drive)) + 0.10 * (1.0 - penalty),
                    ),
                )

                new_activation[aid] = act
                new_phase[aid] = phase
                new_coherence[aid] = coherence

            for aid, agent in self.agents.items():
                agent.activation = new_activation[aid]
                agent.phase = new_phase[aid]
                agent.coherence = new_coherence[aid]
                agent.halo_strength = 0.35 + 0.8 * agent.coherence
                self.activation_history.setdefault(aid, []).append(agent.activation)
                self.phase_history.setdefault(aid, []).append(agent.phase)
                self.activation_history[aid] = self.activation_history[aid][-self.max_history:]
                self.phase_history[aid] = self.phase_history[aid][-self.max_history:]

            self.sim_step += 1
            entropy = self._human_organized_entropy()
            resonance = self._spatial_semantics()["mean_resonance"]
            line = f"step={self.sim_step:03d} entropy={entropy:.3f} resonance={resonance:.3f} band={self._creativity_band_status()}"
            self.sim_trace_box.insert("end", line + "\n")
            self.sim_trace_box.see("end")
            self.sim_status_var.set(line)

        self.redraw_scene()

    # --------------------------------------------------------
    # Compiler
    # --------------------------------------------------------

    def _scene_equations(self) -> List[str]:
        return [
            "a_i(t+1)=tanh(0.55 a_i + 0.35 Σ_j W_ij r_ij a_j(t-τ_ij) + 0.25 A_i + 0.18 S_i - 0.22 P_i + ξ_i)",
            "θ_i(t+1)=θ_i + ω_i + K Σ_j W_ij sin(θ_j(t-τ_ij)-θ_i-τ_ij)",
            "r_ij=0.5+0.5 cos(θ_i-θ_j-τ_ij)",
            "H_i=-Σ_k p_{ik} log_2 p_{ik}",
            "P_i=max(0,H_min-H_i)+max(0,H_i-H_max)",
        ]

    def _compile_scene_dict(self) -> Dict:
        entropy = self._human_organized_entropy()
        semantics = self._spatial_semantics()
        radius = self._adjacency_spectral_radius()
        scene_nodes = []
        for agent in self.agents.values():
            fields = self._field_membership_for_point(agent.x, agent.y)
            artifact_prompts = self._artifact_prompts_for_agent(agent)
            emin, emax = self._field_targets_for_agent(agent)
            prompt = (
                f"Role={agent.role}. "
                f"Prompt seed={agent.prompt_seed or 'none'}. "
                f"Spatial fields={fields or ['global']}. "
                f"Entropy target={agent.entropy_bias:.2f}. "
                f"Allowed band=[{emin:.2f},{emax:.2f}]. "
                f"Swirl recursion budget={agent.recursion_depth}. "
                f"Nearby artifacts={' | '.join(artifact_prompts) if artifact_prompts else 'none'}."
            )
            scene_nodes.append(
                {
                    "id": agent.node_id,
                    "kind": "agent",
                    "label": agent.name,
                    "role": agent.role,
                    "x": round(agent.x, 2),
                    "y": round(agent.y, 2),
                    "phase": round(agent.phase, 4),
                    "frequency": round(agent.frequency, 4),
                    "activation": round(agent.activation, 4),
                    "coherence": round(agent.coherence, 4),
                    "entropy_target": round(agent.entropy_bias, 4),
                    "recursion_budget": agent.recursion_depth,
                    "fields": fields,
                    "artifact_prompts": artifact_prompts,
                    "allowed_tools": agent.allowed_tools,
                    "system_prompt": prompt,
                }
            )

        scene_artifacts = []
        for art in self.artifacts.values():
            scene_artifacts.append(
                {
                    "id": art.artifact_id,
                    "kind": art.kind,
                    "text": art.text,
                    "weight": art.weight,
                    "x": round(art.x, 2),
                    "y": round(art.y, 2),
                    "prompt_mode": art.prompt_mode,
                }
            )

        scene_edges = []
        for edge in self.edges.values():
            if edge.source_id not in self.agents or edge.target_id not in self.agents:
                continue
            a = self.agents[edge.source_id]
            b = self.agents[edge.target_id]
            scene_edges.append(
                {
                    "id": edge.edge_id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "interaction": edge.interaction,
                    "strength": round(edge.tie_strength, 4),
                    "phase_lag": round(edge.phase_lag, 4),
                    "curve": round(edge.curve, 4),
                    "bandwidth": round(edge.bandwidth, 4),
                    "recurrence": round(edge.recurrence, 4),
                    "spatial_affinity": round(self._distance_affinity(a, b), 4),
                    "resonance": round(self._phase_resonance(a, b, edge.phase_lag), 4),
                    "notes": "phase-aware recurrent exchange",
                }
            )

        scene_knots = []
        for knot in self.knots.values():
            scene_knots.append(
                {
                    "id": knot.knot_id,
                    "sync_threshold": round(knot.sync_threshold, 4),
                    "quorum": knot.quorum,
                    "attached_agent_ids": list(knot.attached_agent_ids),
                    "x": round(knot.x, 2),
                    "y": round(knot.y, 2),
                }
            )

        scene_fields = []
        for zone in self.fields.values():
            scene_fields.append(
                {
                    "id": zone.zone_id,
                    "label": zone.label,
                    "theme": zone.theme,
                    "entropy_min": zone.entropy_min,
                    "entropy_max": zone.entropy_max,
                    "bounds": [round(zone.x1, 2), round(zone.y1, 2), round(zone.x2, 2), round(zone.y2, 2)],
                }
            )

        scene = {
            "concepts": {
                "human_organized_entropy": round(entropy, 4),
                "spatial_semantics": semantics,
                "spectral_radius": round(radius, 4),
                "phase_lag_resonance": "Loopties preserve delayed synchronization rather than instant agreement.",
                "artifact_placement_as_prompt": "Artifacts contribute prompt priors to nearby agents as Gaussian-weighted context.",
                "entropy_bounds": {
                    "min": round(float(self.entropy_min_var.get()), 4),
                    "max": round(float(self.entropy_max_var.get()), 4),
                    "status": self._creativity_band_status(),
                },
            },
            "nodes": scene_nodes,
            "artifacts": scene_artifacts,
            "edges": scene_edges,
            "knots": scene_knots,
            "fields": scene_fields,
            "equations": self._scene_equations(),
            "compiler_hints": {
                "goal": "Compile the visual canvas into a runtime graph for agentized LLM orchestration.",
                "swirl_recursion": "Use recursion budget to allocate reflective turns.",
                "knot_synchronization": "Treat knots as quorum gates before downstream deployment.",
                "looptie_grammar": "Curved ties are recurrent phase-lag channels, not simple DAG edges.",
            },
        }
        return scene

    def _heuristic_runtime_graph(self, scene: Dict) -> RuntimeGraphSpec:
        nodes: List[RuntimeNode] = []
        barriers: List[RuntimeBarrier] = []
        edges: List[RuntimeEdge] = []

        for node in scene["nodes"]:
            nodes.append(
                RuntimeNode(
                    id=node["id"],
                    kind=node["kind"],
                    label=node["label"],
                    role=node["role"],
                    system_prompt=node["system_prompt"],
                    tools=node["allowed_tools"],
                    recursion_budget=node["recursion_budget"],
                    entropy_target=node["entropy_target"],
                    phase=node["phase"],
                    field_membership=node["fields"],
                    prompt_artifacts=node["artifact_prompts"],
                )
            )

        for edge in scene["edges"]:
            edges.append(
                RuntimeEdge(
                    id=edge["id"],
                    source=edge["source"],
                    target=edge["target"],
                    interaction=edge["interaction"],
                    strength=edge["strength"],
                    phase_lag=edge["phase_lag"],
                    bandwidth=edge["bandwidth"],
                    recurrence=edge["recurrence"],
                    resonance=edge["resonance"],
                    notes=edge["notes"],
                )
            )

        for knot in scene["knots"]:
            barriers.append(
                RuntimeBarrier(
                    id=knot["id"],
                    threshold=knot["sync_threshold"],
                    quorum=knot["quorum"],
                    attached_agents=knot["attached_agent_ids"],
                    release_rule=(
                        f"Release when at least {knot['quorum']} inbound agents exceed coherence "
                        f"{knot['sync_threshold']:.2f}."
                    ),
                )
            )
            for agent_id in knot["attached_agent_ids"]:
                edges.append(
                    RuntimeEdge(
                        id=f"{knot['id']}::{agent_id}",
                        source=agent_id,
                        target=knot["id"],
                        interaction="knot_sync",
                        strength=0.85,
                        phase_lag=0.0,
                        bandwidth=1.0,
                        recurrence=0.0,
                        resonance=0.80,
                        notes="barrier synchronization path",
                    )
                )

        role_groups = {
            "ideation": [n["id"] for n in scene["nodes"] if any(k in n["role"].lower() for k in ["dream", "scout", "research", "general"])]
                        or n["entropy_target"] >= 0.55,
            "convergence": [n["id"] for n in scene["nodes"] if n["recursion_budget"] > 0 or 0.35 <= n["entropy_target"] < 0.55],
            "verification": [n["id"] for n in scene["nodes"] if any(k in n["role"].lower() for k in ["critic", "verify", "judge", "synth"])]
                           or n["entropy_target"] < 0.35,
            "deployment": [n["id"] for n in scene["nodes"] if "deploy" in n["role"].lower()],
        }
        schedule = [
            RuntimeScheduleStep(
                stage="ideation",
                node_ids=role_groups["ideation"] or [n["id"] for n in scene["nodes"][: max(1, len(scene["nodes"]) // 3)]],
                entry_criterion="Canvas compiled successfully.",
                exit_criterion="Mean activation exceeds 0.18 or local novelty artifacts are exhausted.",
            ),
            RuntimeScheduleStep(
                stage="convergence",
                node_ids=role_groups["convergence"] or [n["id"] for n in scene["nodes"]],
                entry_criterion="At least one ideation node has emitted candidate artifacts or proposals.",
                exit_criterion="Knot barriers reach quorum and resonance crosses threshold.",
            ),
            RuntimeScheduleStep(
                stage="verification",
                node_ids=role_groups["verification"] or [n["id"] for n in scene["nodes"][-max(1, len(scene["nodes"]) // 3):]],
                entry_criterion="Convergence stage produced coherent draft outputs.",
                exit_criterion="All active barriers release and critiques are resolved.",
            ),
            RuntimeScheduleStep(
                stage="deployment",
                node_ids=role_groups["deployment"] or [b.id for b in barriers],
                entry_criterion="Verification passed and deployment-capable nodes are available.",
                exit_criterion="Delivery task completed or runtime enters hold state.",
            ),
        ]

        policy = RuntimePolicy(
            entropy_min=scene["concepts"]["entropy_bounds"]["min"],
            entropy_max=scene["concepts"]["entropy_bounds"]["max"],
            creativity_mode=scene["concepts"]["entropy_bounds"]["status"],
            sync_rule="Knot barriers control release; no downstream deployment fires before barrier release.",
            deployment_rule="Only nodes with deploy capability or released barriers may trigger deployment actions.",
            equations=scene["equations"],
        )

        notes = [
            f"Entropy = {scene['concepts']['human_organized_entropy']:.3f}",
            f"Mean affinity = {scene['concepts']['spatial_semantics']['mean_affinity']:.3f}",
            f"Mean resonance = {scene['concepts']['spatial_semantics']['mean_resonance']:.3f}",
            f"Spectral radius = {scene['concepts']['spectral_radius']:.3f}",
            "Artifact placement compiled into prompt priors for nearby agents.",
            "Swirl recursion compiled into explicit reflective budgets.",
            "Loopties compiled as delayed recurrent channels rather than simple DAG edges.",
        ]

        return RuntimeGraphSpec(
            title="Looptie Runtime Graph",
            summary="Compiled from a resonance canvas with human-organized entropy, field semantics, and phase-lag synchronization.",
            nodes=nodes,
            edges=edges,
            barriers=barriers,
            schedule=schedule,
            policies=policy,
            compiler_notes=notes,
        )

    def compile_local(self) -> None:
        scene = self._compile_scene_dict()
        runtime = self._heuristic_runtime_graph(scene)
        self.last_runtime = runtime
        self._write_output(runtime.model_dump_json(indent=2))
        self.compiler_summary_box.delete("1.0", "end")
        self.compiler_summary_box.insert(
            "end",
            json.dumps(
                {
                    "scene_metrics": scene["concepts"],
                    "counts": {
                        "agents": len(self.agents),
                        "artifacts": len(self.artifacts),
                        "edges": len(self.edges),
                        "knots": len(self.knots),
                        "fields": len(self.fields),
                    },
                    "schedule": [step.model_dump() for step in runtime.schedule],
                },
                indent=2,
            ),
        )
        self._log("Local compiler produced runtime graph")

    def compile_with_gpt(self) -> None:
        try:
            api_key = self.api_key_var.get().strip() or os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError("No API key found. Set OPENAI_API_KEY or paste it into the field.")
            self.client = OpenAI(api_key=api_key)
            scene = self._compile_scene_dict()
            system_prompt = (
                "You are an advanced compiler for a spatial multi-agent interface. "
                "The input canvas uses human-organized entropy, spatial semantics, looptie grammar, swirl recursion, "
                "knot synchronization, phase-lag resonance, artifact placement as prompt, and entropy bounds for creativity. "
                "Produce a strict runtime graph that preserves artistic topology while making execution and policy precise."
            )
            response = self.client.responses.parse(
                model=self.model_var.get().strip() or "gpt-5.4",
                input=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": "Compile the following resonance canvas into a runtime graph.\n\n" + json.dumps(scene, indent=2),
                    },
                ],
                text_format=RuntimeGraphSpec,
                reasoning={"effort": self.reasoning_var.get().strip() or "high"},
            )
            runtime = response.output_parsed
            if runtime is None:
                raise ValueError("The model returned no parsed runtime graph.")
            self.last_runtime = runtime
            self._write_output(runtime.model_dump_json(indent=2))
            self.compiler_summary_box.delete("1.0", "end")
            self.compiler_summary_box.insert("end", json.dumps(scene["concepts"], indent=2))
            self._log("GPT compiler produced runtime graph")
        except Exception as exc:
            self._log(f"Compile error: {exc}")
            self._write_output(json.dumps({"error": str(exc)}, indent=2))

    # --------------------------------------------------------
    # Export and project persistence
    # --------------------------------------------------------

    def _project_payload(self) -> Dict:
        return {
            "agents": [asdict(v) for v in self.agents.values()],
            "artifacts": [asdict(v) for v in self.artifacts.values()],
            "edges": [asdict(v) for v in self.edges.values()],
            "knots": [asdict(v) for v in self.knots.values()],
            "fields": [asdict(v) for v in self.fields.values()],
            "settings": {
                "entropy_min": float(self.entropy_min_var.get()),
                "entropy_max": float(self.entropy_max_var.get()),
                "model": self.model_var.get(),
                "reasoning": self.reasoning_var.get(),
            },
        }

    def save_project(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Looptie project",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._project_payload(), f, indent=2)
        self._log(f"Saved project to {path}")

    def load_project(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load Looptie project")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.clear_canvas()

        self.agents = {}
        self.artifacts = {}
        self.edges = {}
        self.knots = {}
        self.fields = {}
        self.activation_history = {}
        self.phase_history = {}

        for data in payload.get("agents", []):
            data["canvas_items"] = []
            agent = AgentNode(**data)
            self.agents[agent.node_id] = agent
            self.activation_history[agent.node_id] = [agent.activation]
            self.phase_history[agent.node_id] = [agent.phase]
        for data in payload.get("artifacts", []):
            data["canvas_items"] = []
            art = ArtifactNode(**data)
            self.artifacts[art.artifact_id] = art
        for data in payload.get("edges", []):
            data["canvas_items"] = []
            edge = EdgeLink(**data)
            self.edges[edge.edge_id] = edge
        for data in payload.get("knots", []):
            data["canvas_items"] = []
            knot = KnotNode(**data)
            self.knots[knot.knot_id] = knot
        for data in payload.get("fields", []):
            data["canvas_items"] = []
            zone = FieldZone(**data)
            self.fields[zone.zone_id] = zone

        settings = payload.get("settings", {})
        self.entropy_min_var.set(settings.get("entropy_min", 0.25))
        self.entropy_max_var.set(settings.get("entropy_max", 0.80))
        self.model_var.set(settings.get("model", "gpt-5.4"))
        self.reasoning_var.set(settings.get("reasoning", "high"))

        self._sync_counters()
        self.redraw_scene()
        self._log(f"Loaded project from {path}")

    def export_runtime_json(self) -> None:
        if self.last_runtime is None:
            self.compile_local()
        runtime = self.last_runtime
        if runtime is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export runtime graph JSON",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(runtime.model_dump_json(indent=2))
        self._log(f"Exported runtime JSON to {path}")

    def export_runtime_python(self) -> None:
        if self.last_runtime is None:
            self.compile_local()
        runtime = self.last_runtime
        if runtime is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            title="Export runtime executor stub",
        )
        if not path:
            return
        content = self._runtime_python_stub(runtime)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._log(f"Exported runtime executor stub to {path}")

    def _runtime_python_stub(self, runtime: RuntimeGraphSpec) -> str:
        payload = runtime.model_dump()
        return f'''"""Auto-generated runtime stub from Looptie Studio Pro."""
import json
from dataclasses import dataclass
from typing import Dict, List

RUNTIME = {json.dumps(payload, indent=2)}


def load_runtime() -> Dict:
    return RUNTIME


def stage_order() -> List[str]:
    return [step["stage"] for step in RUNTIME["schedule"]]


def print_summary() -> None:
    print(RUNTIME["title"])
    print(RUNTIME["summary"])
    print("nodes:", len(RUNTIME["nodes"]))
    print("edges:", len(RUNTIME["edges"]))
    print("barriers:", len(RUNTIME["barriers"]))
    print("creativity_mode:", RUNTIME["policies"]["creativity_mode"])


if __name__ == "__main__":
    print_summary()
'''

    # --------------------------------------------------------
    # Scene helpers
    # --------------------------------------------------------

    def randomize_phases(self) -> None:
        for agent in self.agents.values():
            agent.phase = random.uniform(-math.pi, math.pi)
        self.redraw_scene()
        self._log("Randomized agent phases")

    def auto_layout(self) -> None:
        if not self.agents:
            return
        ids = list(self.agents.keys())
        center_x = 660
        center_y = 430
        radius = 220
        for idx, aid in enumerate(ids):
            angle = (2 * math.pi * idx) / max(1, len(ids))
            self.agents[aid].x = center_x + radius * math.cos(angle)
            self.agents[aid].y = center_y + radius * math.sin(angle)
        for idx, artifact in enumerate(self.artifacts.values()):
            artifact.x = center_x + (radius + 170) * math.cos((2 * math.pi * idx) / max(1, len(self.artifacts)))
            artifact.y = center_y + (radius + 170) * math.sin((2 * math.pi * idx) / max(1, len(self.artifacts)))
        for knot in self.knots.values():
            knot.attached_agent_ids = self._agents_near_point(knot.x, knot.y, 220)
        self.redraw_scene()
        self._log("Auto-layout applied")

    def _sync_counters(self) -> None:
        def _max_suffix(values: List[str], prefix: str) -> int:
            best = 0
            for value in values:
                if value.startswith(prefix):
                    try:
                        best = max(best, int(value.split("_")[-1]))
                    except ValueError:
                        pass
            return best

        self.agent_counter = _max_suffix(list(self.agents.keys()), "agent") + 1
        self.artifact_counter = _max_suffix(list(self.artifacts.keys()), "artifact") + 1
        self.edge_counter = _max_suffix(list(self.edges.keys()), "edge") + 1
        self.knot_counter = _max_suffix(list(self.knots.keys()), "knot") + 1
        self.zone_counter = _max_suffix(list(self.fields.keys()), "zone") + 1

    def _populate_demo_scene(self) -> None:
        self.clear_canvas()
        self.entropy_min_var.set(0.22)
        self.entropy_max_var.set(0.81)

        self.fields["zone_1"] = FieldZone("zone_1", "ideation field", 90, 90, 610, 390, 0.45, 0.88, "research")
        self.fields["zone_2"] = FieldZone("zone_2", "verification field", 740, 120, 1180, 420, 0.16, 0.48, "critique")
        self.fields["zone_3"] = FieldZone("zone_3", "deployment field", 900, 520, 1280, 820, 0.12, 0.34, "deploy")

        def add_demo_agent(node_id: str, name: str, x: float, y: float, role: str, entropy_bias: float, recursion: int, phase: float, freq: float) -> None:
            agent = AgentNode(
                node_id=node_id,
                name=name,
                x=x,
                y=y,
                role=role,
                prompt_seed=f"{role} prompt seed",
                phase=phase,
                frequency=freq,
                entropy_bias=entropy_bias,
                recursion_depth=recursion,
                activation=0.0,
                coherence=0.50,
                halo_strength=0.55,
                allowed_tools=["reason", "reflect", "summarize"] + (["deploy"] if "deploy" in role else []),
            )
            self.agents[node_id] = agent
            self.activation_history[node_id] = [0.0]
            self.phase_history[node_id] = [phase]

        add_demo_agent("agent_1", "Dreamer", 250, 190, "research dreamer", 0.76, 2, 0.2, 0.04)
        add_demo_agent("agent_2", "Scout", 450, 250, "research scout", 0.67, 1, -0.8, 0.05)
        add_demo_agent("agent_3", "Synth", 730, 340, "synthesizer", 0.46, 2, 1.0, 0.03)
        add_demo_agent("agent_4", "Critic", 970, 250, "critic verifier", 0.26, 1, -1.2, 0.02)
        add_demo_agent("agent_5", "Deployer", 1080, 640, "deploy operator", 0.18, 0, 0.7, 0.015)

        self.artifacts["artifact_1"] = ArtifactNode("artifact_1", "gallery board: asymmetry, orbit, memory basin", 250, 360, 1.25, "vision")
        self.artifacts["artifact_2"] = ArtifactNode("artifact_2", "note: humans shape entropy, not erase it", 470, 120, 1.00, "prompt")
        self.artifacts["artifact_3"] = ArtifactNode("artifact_3", "spec: only deploy after knot release", 955, 560, 1.20, "constraint")

        self.edges["edge_1"] = EdgeLink("edge_1", "agent_1", "agent_2", 1.2, 0.4, 55.0, 1.2, 0.9)
        self.edges["edge_2"] = EdgeLink("edge_2", "agent_2", "agent_3", 1.0, -0.2, -46.0, 1.0, 0.8)
        self.edges["edge_3"] = EdgeLink("edge_3", "agent_3", "agent_4", 0.92, 0.65, 40.0, 0.95, 0.6)
        self.edges["edge_4"] = EdgeLink("edge_4", "agent_4", "agent_5", 0.78, 0.0, -32.0, 0.9, 0.3)
        self.edges["edge_5"] = EdgeLink("edge_5", "agent_1", "agent_3", 0.72, -0.9, 78.0, 0.75, 0.75)

        self.knots["knot_1"] = KnotNode("knot_1", 840, 470, 0.72, 2, ["agent_3", "agent_4", "agent_5"])

        self._sync_counters()
        self.redraw_scene()
        self._log("Loaded demo resonance scene")


def main() -> None:
    app = AdvancedLooptieStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
