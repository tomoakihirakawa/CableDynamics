"""Cable input parameter types for the cable_solver binary.

Two dataclasses live here:

- ``CableParams`` — a single cable, the original schema. Maps 1:1 to the
  legacy single-line JSON form (`point_a`, `point_b`, `cable_length`, ...)
  read by ``cable/cable_solver.cpp::main``. Backward compatible — existing
  pycable callers and the original test suite still use this.

- ``LumpedCableSystemParams`` — Phase 4 (2026-04-12) addition. Holds a
  list of ``CableParams`` plus shared top-level scalars (gravity, mode,
  solver settings). Round-trips both the legacy single-line JSON
  (when the list has exactly one cable, with the original schema) and
  the new multi-line ``mooring_<name>`` flat format used by the BEM input
  reader and the multi-line `cable_solver.cpp` mode. The two formats are
  auto-detected on read: if the JSON has any `mooring_*` keys, we treat
  it as multi-line; otherwise it's the legacy single-line form.

Both dataclasses emit *natural* JSON (numbers unquoted, arrays mixed),
which the C++ ``parseJSON`` in lib/include/basic.hpp accepts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Tuple


Vec3 = Tuple[float, float, float]


@dataclass
class CableParams:
    """Parameters for a single cable_solver equilibrium run."""

    # --- Geometry ---
    point_a: Vec3 = (500.0, 0.0, -58.0)
    point_b: Vec3 = (0.0, 0.0, 0.0)
    cable_length: float = 522.0
    n_segments: int = 40

    # --- Material ---
    line_density: float = 348.5      # [kg/m]
    EA: float = 1.4e9                # [N]
    damping: float = 0.5             # artificial relaxation coefficient
    diameter: float = 0.132          # [m]
    gravity: float = 9.81            # [m/s^2]

    # --- Solver ---
    mode: str = "equilibrium"
    max_equilibrium_steps: int = 500_000
    equilibrium_tol: float = 0.01
    snapshot_interval: int = 10_000

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a dict matching the cable_solver input JSON schema.

        Numbers are unquoted, arrays are natural. The cable_solver
        parseJSON walks this in string form internally, but on-disk the
        file is human-readable standard JSON.
        """
        return {
            "point_a": [float(x) for x in self.point_a],
            "point_b": [float(x) for x in self.point_b],
            "cable_length": float(self.cable_length),
            "n_segments": int(self.n_segments),
            "line_density": float(self.line_density),
            "EA": float(self.EA),
            "damping": float(self.damping),
            "diameter": float(self.diameter),
            "gravity": float(self.gravity),
            "mode": str(self.mode),
            "max_equilibrium_steps": int(self.max_equilibrium_steps),
            "equilibrium_tol": float(self.equilibrium_tol),
            "snapshot_interval": int(self.snapshot_interval),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CableParams":
        """Build CableParams from a dict, filling missing keys with defaults."""
        defaults = cls()
        return cls(
            point_a=tuple(d.get("point_a", defaults.point_a)),
            point_b=tuple(d.get("point_b", defaults.point_b)),
            cable_length=float(d.get("cable_length", defaults.cable_length)),
            n_segments=int(d.get("n_segments", defaults.n_segments)),
            line_density=float(d.get("line_density", defaults.line_density)),
            EA=float(d.get("EA", defaults.EA)),
            damping=float(d.get("damping", defaults.damping)),
            diameter=float(d.get("diameter", defaults.diameter)),
            gravity=float(d.get("gravity", defaults.gravity)),
            mode=str(d.get("mode", defaults.mode)),
            max_equilibrium_steps=int(
                d.get("max_equilibrium_steps", defaults.max_equilibrium_steps)
            ),
            equilibrium_tol=float(d.get("equilibrium_tol", defaults.equilibrium_tol)),
            snapshot_interval=int(d.get("snapshot_interval", defaults.snapshot_interval)),
        )

    def write_json(self, path: Path | str) -> None:
        """Write the params as a cable_solver-compatible input.json."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def read_json(cls, path: Path | str) -> "CableParams":
        """Load CableParams from a cable_solver input.json."""
        with Path(path).open() as f:
            return cls.from_dict(json.load(f))


# ---------------------------------------------------------------------------
# Phase 4 (2026-04-12): Multi-cable system params
# ---------------------------------------------------------------------------

# Default name used when promoting a single CableParams into a one-element
# system (e.g. when reading a legacy single-line JSON).
DEFAULT_SINGLE_CABLE_NAME = "cable"


@dataclass
class CableSpec:
    """One cable inside a ``LumpedCableSystemParams``.

    Mirrors the BEM/cable_solver multi-line flat 13-element schema:
    ``[name, ax, ay, az, bx, by, bz, total_length, n_points, line_density,
    EA, damping, diameter]``.

    Note ``n_points`` (= ``n_segments + 1``), matching the BEM JSON form.
    """

    name: str = DEFAULT_SINGLE_CABLE_NAME
    point_a: Vec3 = (500.0, 0.0, -58.0)
    point_b: Vec3 = (0.0, 0.0, 0.0)
    cable_length: float = 522.0
    n_points: int = 41  # = n_segments + 1
    line_density: float = 348.5
    EA: float = 1.4e9
    damping: float = 0.5
    diameter: float = 0.132

    @property
    def n_segments(self) -> int:
        return max(0, int(self.n_points) - 1)

    def to_flat_array(self) -> list[Any]:
        """Encode as the 13-element BEM mooring flat array."""
        return [
            str(self.name),
            float(self.point_a[0]), float(self.point_a[1]), float(self.point_a[2]),
            float(self.point_b[0]), float(self.point_b[1]), float(self.point_b[2]),
            float(self.cable_length),
            int(self.n_points),
            float(self.line_density),
            float(self.EA),
            float(self.damping),
            float(self.diameter),
        ]

    @classmethod
    def from_flat_array(cls, value: Iterable[Any]) -> "CableSpec":
        """Decode a BEM mooring flat array (13 elements)."""
        v = list(value)
        if len(v) != 13:
            raise ValueError(f"mooring flat array must have 13 elements, got {len(v)}")
        return cls(
            name=str(v[0]),
            point_a=(float(v[1]), float(v[2]), float(v[3])),
            point_b=(float(v[4]), float(v[5]), float(v[6])),
            cable_length=float(v[7]),
            n_points=int(v[8]),
            line_density=float(v[9]),
            EA=float(v[10]),
            damping=float(v[11]),
            diameter=float(v[12]),
        )

    @classmethod
    def from_cable_params(cls, params: "CableParams",
                          name: str = DEFAULT_SINGLE_CABLE_NAME) -> "CableSpec":
        """Promote a CableParams (legacy single-line) to a CableSpec."""
        return cls(
            name=name,
            point_a=tuple(params.point_a),
            point_b=tuple(params.point_b),
            cable_length=float(params.cable_length),
            n_points=int(params.n_segments) + 1,
            line_density=float(params.line_density),
            EA=float(params.EA),
            damping=float(params.damping),
            diameter=float(params.diameter),
        )

    def to_cable_params(self,
                        gravity: float = 9.81,
                        mode: str = "equilibrium",
                        max_equilibrium_steps: int = 500_000,
                        equilibrium_tol: float = 0.01,
                        snapshot_interval: int = 10_000) -> "CableParams":
        """Demote to a CableParams for the legacy single-line GUI / form."""
        return CableParams(
            point_a=tuple(self.point_a),
            point_b=tuple(self.point_b),
            cable_length=float(self.cable_length),
            n_segments=int(self.n_segments),
            line_density=float(self.line_density),
            EA=float(self.EA),
            damping=float(self.damping),
            diameter=float(self.diameter),
            gravity=float(gravity),
            mode=str(mode),
            max_equilibrium_steps=int(max_equilibrium_steps),
            equilibrium_tol=float(equilibrium_tol),
            snapshot_interval=int(snapshot_interval),
        )


@dataclass
class LumpedCableSystemParams:
    """A collection of cables sharing top-level solver scalars.

    Round-trips two on-disk JSON formats:

    1. **Legacy single-line** — when ``cables`` has exactly one entry and
       the cable's name is the default ``"cable"``. Output uses the
       historical flat keys (``point_a``, ``point_b``, ``cable_length``, ...).
       Loaded by ``cable_solver.cpp`` legacy path.

    2. **Multi-line BEM-compatible** — when ``cables`` has more than one
       entry, or when the user explicitly requested the multi-line format.
       Output uses ``mooring_<name>`` flat 13-element arrays. Loaded by
       ``cable_solver.cpp``'s multi-line auto-detected path.
    """

    cables: list[CableSpec] = field(default_factory=list)

    # Top-level shared scalars
    gravity: float = 9.81
    mode: str = "equilibrium"
    max_equilibrium_steps: int = 500_000
    equilibrium_tol: float = 0.01
    snapshot_interval: int = 10_000

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_cable_params(cls, params: "CableParams",
                          name: str = DEFAULT_SINGLE_CABLE_NAME) -> "LumpedCableSystemParams":
        """Wrap a single legacy CableParams as a one-cable system."""
        return cls(
            cables=[CableSpec.from_cable_params(params, name=name)],
            gravity=float(params.gravity),
            mode=str(params.mode),
            max_equilibrium_steps=int(params.max_equilibrium_steps),
            equilibrium_tol=float(params.equilibrium_tol),
            snapshot_interval=int(params.snapshot_interval),
        )

    def is_single_legacy(self) -> bool:
        """Return True if this system can be safely written as legacy single-line."""
        return len(self.cables) == 1 and self.cables[0].name == DEFAULT_SINGLE_CABLE_NAME

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Render to a dict in either single-line or multi-line schema.

        Routing rule:
        - Empty system: top-level scalars only (degenerate)
        - Single cable with default name "cable": legacy single-line schema
        - Otherwise: multi-line ``mooring_<name>`` schema
        """
        if not self.cables:
            return {
                "gravity": float(self.gravity),
                "mode": str(self.mode),
                "max_equilibrium_steps": int(self.max_equilibrium_steps),
                "equilibrium_tol": float(self.equilibrium_tol),
                "snapshot_interval": int(self.snapshot_interval),
            }

        if self.is_single_legacy():
            # Legacy single-line schema (matches CableParams.to_dict()).
            return self.cables[0].to_cable_params(
                gravity=self.gravity,
                mode=self.mode,
                max_equilibrium_steps=self.max_equilibrium_steps,
                equilibrium_tol=self.equilibrium_tol,
                snapshot_interval=self.snapshot_interval,
            ).to_dict()

        # Multi-line BEM-compatible schema.
        d: dict[str, Any] = {}
        for cable in self.cables:
            d[f"mooring_{cable.name}"] = cable.to_flat_array()
        d["gravity"] = float(self.gravity)
        d["mode"] = str(self.mode)
        d["max_equilibrium_steps"] = int(self.max_equilibrium_steps)
        d["equilibrium_tol"] = float(self.equilibrium_tol)
        d["snapshot_interval"] = int(self.snapshot_interval)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LumpedCableSystemParams":
        """Auto-detect single-line vs multi-line vs per-cable and build.

        Detection order:
        1. ``end_a_position`` present → per-cable format (single cable)
        2. Any ``mooring_*`` / ``cable_*`` key with 13-element list → multi-line
        3. Otherwise → legacy single-line (``point_a`` / ``point_b``)
        """
        defaults = cls()

        # --- Per-cable format ---
        if "end_a_position" in d:
            pc = PerCableParams.from_dict(d)
            spec = CableSpec(
                name=pc.name,
                point_a=tuple(pc.end_a_position),
                point_b=tuple(pc.end_b_position),
                cable_length=pc.cable_length,
                n_points=pc.n_points,
                line_density=pc.line_density,
                EA=pc.EA,
                damping=pc.damping,
                diameter=pc.diameter,
            )
            return cls(
                cables=[spec],
                gravity=pc.gravity,
                mode=pc.mode,
                max_equilibrium_steps=pc.max_equilibrium_steps,
                equilibrium_tol=pc.equilibrium_tol,
                snapshot_interval=pc.snapshot_interval,
            )

        # --- Multi-line format ---
        multi_keys: list[tuple[str, list[Any]]] = []
        for key, value in d.items():
            if not isinstance(value, list):
                continue
            if (key.startswith("mooring_") or key.startswith("cable_")) and len(value) == 13:
                multi_keys.append((key, value))

        if multi_keys:
            cables = [CableSpec.from_flat_array(v) for _, v in multi_keys]
            return cls(
                cables=cables,
                gravity=float(d.get("gravity", defaults.gravity)),
                mode=str(d.get("mode", defaults.mode)),
                max_equilibrium_steps=int(d.get("max_equilibrium_steps", defaults.max_equilibrium_steps)),
                equilibrium_tol=float(d.get("equilibrium_tol", defaults.equilibrium_tol)),
                snapshot_interval=int(d.get("snapshot_interval", defaults.snapshot_interval)),
            )

        # --- Legacy single-line format ---
        legacy = CableParams.from_dict(d)
        return cls.from_cable_params(legacy)

    def write_json(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def read_json(cls, path: Path | str) -> "LumpedCableSystemParams":
        """Read a cable JSON file (any format) or a settings.json.

        Detection order:
        1. ``input_files`` key → settings mode: load each referenced file
        2. ``end_a_position`` → per-cable
        3. ``mooring_*`` 13-element → multi-line
        4. ``point_a`` → legacy single-line
        """
        path = Path(path)
        with path.open() as f:
            d = json.load(f)

        # --- Settings mode ---
        if "input_files" in d:
            input_dir = path.parent
            all_cables: list[CableSpec] = []
            for fname in d["input_files"]:
                cable_path = input_dir / fname
                sub = cls.read_json(cable_path)
                all_cables.extend(sub.cables)
            defaults = cls()
            return cls(
                cables=all_cables,
                gravity=float(d.get("gravity", defaults.gravity)),
                mode=str(d.get("mode", defaults.mode)),
                max_equilibrium_steps=int(d.get("max_equilibrium_steps", defaults.max_equilibrium_steps)),
                equilibrium_tol=float(d.get("equilibrium_tol", defaults.equilibrium_tol)),
                snapshot_interval=int(d.get("snapshot_interval", defaults.snapshot_interval)),
            )

        return cls.from_dict(d)


# ---------------------------------------------------------------------------
# Per-Cable JSON format (new canonical form)
# ---------------------------------------------------------------------------

@dataclass
class PerCableParams:
    """Self-contained single-cable JSON — the new canonical format.

    Each cable file declares its own endpoints, material properties, and
    (optionally) body labels and motion prescriptions. Both BEM and
    cable_solver read this format.

    Keys map 1:1 to flat JSON keys accepted by ``cable_solver.cpp``'s
    per-cable detection path (``end_a_position`` presence).
    """

    name: str = "cable"

    # --- Endpoints ---
    end_a_position: Vec3 = (0.0, 0.0, 0.0)
    end_b_position: Vec3 = (0.0, 0.0, 0.0)
    end_a_body: str = ""      # BEM linkage label ("" = world / fixed)
    end_b_body: str = ""

    # --- Endpoint motion (Phase B: dynamic mode) ---
    end_a_motion: str = "fixed"
    end_b_motion: str = "fixed"
    # sinusoidal motion params (used when motion != "fixed")
    end_a_motion_dof: str = ""
    end_a_motion_amplitude: float = 0.0
    end_a_motion_frequency: float = 0.0
    end_a_motion_phase: float = 0.0
    end_b_motion_dof: str = ""
    end_b_motion_amplitude: float = 0.0
    end_b_motion_frequency: float = 0.0
    end_b_motion_phase: float = 0.0

    # --- Initial condition ---
    initial_condition: str = "length"   # "length" or "tension"
    tension: float = 0.0               # legacy: single target tension [N]
    tension_top: float = 0.0           # target top-end tension [N]
    tension_bottom: float = 0.0        # target bottom-end tension [N]

    # --- Cable properties ---
    cable_length: float = 100.0
    n_points: int = 41
    line_density: float = 348.5    # kg/m
    EA: float = 1.4e9              # N
    damping: float = 0.5
    diameter: float = 0.132        # m

    # --- Solver ---
    gravity: float = 9.81
    mode: str = "equilibrium"
    max_equilibrium_steps: int = 500_000
    equilibrium_tol: float = 0.01
    snapshot_interval: int = 10_000

    # --- Dynamic mode (Phase B) ---
    dt: float = 0.0
    t_end: float = 0.0
    output_interval: float = 0.0

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Render as a flat dict matching the per-cable JSON schema."""
        d: dict[str, Any] = {}
        d["name"] = self.name
        d["end_a_position"] = list(self.end_a_position)
        d["end_b_position"] = list(self.end_b_position)
        if self.end_a_body:
            d["end_a_body"] = self.end_a_body
        if self.end_b_body:
            d["end_b_body"] = self.end_b_body
        if self.end_a_motion != "fixed":
            d["end_a_motion"] = self.end_a_motion
            if self.end_a_motion_dof:
                d["end_a_motion_dof"] = self.end_a_motion_dof
                d["end_a_motion_amplitude"] = self.end_a_motion_amplitude
                d["end_a_motion_frequency"] = self.end_a_motion_frequency
                d["end_a_motion_phase"] = self.end_a_motion_phase
        if self.end_b_motion != "fixed":
            d["end_b_motion"] = self.end_b_motion
            if self.end_b_motion_dof:
                d["end_b_motion_dof"] = self.end_b_motion_dof
                d["end_b_motion_amplitude"] = self.end_b_motion_amplitude
                d["end_b_motion_frequency"] = self.end_b_motion_frequency
                d["end_b_motion_phase"] = self.end_b_motion_phase
        if self.initial_condition != "length":
            d["initial_condition"] = self.initial_condition
        if self.initial_condition == "tension":
            if self.tension_top > 0:
                d["tension_top"] = self.tension_top
            if self.tension_bottom > 0:
                d["tension_bottom"] = self.tension_bottom
            if self.tension > 0 and self.tension_top == 0 and self.tension_bottom == 0:
                d["tension"] = self.tension
        d["cable_length"] = self.cable_length
        d["n_points"] = self.n_points
        d["line_density"] = self.line_density
        d["EA"] = self.EA
        d["damping"] = self.damping
        d["diameter"] = self.diameter
        d["gravity"] = self.gravity
        d["mode"] = self.mode
        d["max_equilibrium_steps"] = self.max_equilibrium_steps
        d["equilibrium_tol"] = self.equilibrium_tol
        d["snapshot_interval"] = self.snapshot_interval
        if self.mode == "dynamic":
            d["dt"] = self.dt
            d["t_end"] = self.t_end
            if self.output_interval > 0:
                d["output_interval"] = self.output_interval
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PerCableParams":
        """Build from a flat dict (per-cable JSON)."""
        def _vec3(key: str, default: Vec3) -> Vec3:
            v = d.get(key)
            if v is not None and len(v) >= 3:
                return (float(v[0]), float(v[1]), float(v[2]))
            return default

        return cls(
            name=str(d.get("name", "cable")),
            end_a_position=_vec3("end_a_position", (0, 0, 0)),
            end_b_position=_vec3("end_b_position", (0, 0, 0)),
            end_a_body=str(d.get("end_a_body", "")),
            end_b_body=str(d.get("end_b_body", "")),
            end_a_motion=str(d.get("end_a_motion", "fixed")),
            end_b_motion=str(d.get("end_b_motion", "fixed")),
            end_a_motion_dof=str(d.get("end_a_motion_dof", "")),
            end_a_motion_amplitude=float(d.get("end_a_motion_amplitude", 0)),
            end_a_motion_frequency=float(d.get("end_a_motion_frequency", 0)),
            end_a_motion_phase=float(d.get("end_a_motion_phase", 0)),
            end_b_motion_dof=str(d.get("end_b_motion_dof", "")),
            end_b_motion_amplitude=float(d.get("end_b_motion_amplitude", 0)),
            end_b_motion_frequency=float(d.get("end_b_motion_frequency", 0)),
            end_b_motion_phase=float(d.get("end_b_motion_phase", 0)),
            initial_condition=str(d.get("initial_condition", "length")),
            tension=float(d.get("tension", 0)),
            tension_top=float(d.get("tension_top", 0)),
            tension_bottom=float(d.get("tension_bottom", 0)),
            cable_length=float(d.get("cable_length", 100)),
            n_points=int(d.get("n_points", 41)),
            line_density=float(d.get("line_density", 348.5)),
            EA=float(d.get("EA", 1.4e9)),
            damping=float(d.get("damping", 0.5)),
            diameter=float(d.get("diameter", 0.132)),
            gravity=float(d.get("gravity", 9.81)),
            mode=str(d.get("mode", "equilibrium")),
            max_equilibrium_steps=int(d.get("max_equilibrium_steps", 500_000)),
            equilibrium_tol=float(d.get("equilibrium_tol", 0.01)),
            snapshot_interval=int(d.get("snapshot_interval", 10_000)),
            dt=float(d.get("dt", 0)),
            t_end=float(d.get("t_end", 0)),
            output_interval=float(d.get("output_interval", 0)),
        )

    def write_json(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def read_json(cls, path: Path | str) -> "PerCableParams":
        with Path(path).open() as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------
    # Conversion from/to legacy formats
    # ------------------------------------------------------------------

    @classmethod
    def from_cable_params(cls, p: "CableParams",
                          name: str = "cable") -> "PerCableParams":
        """Convert a legacy CableParams to per-cable format."""
        return cls(
            name=name,
            end_a_position=tuple(p.point_a),
            end_b_position=tuple(p.point_b),
            cable_length=p.cable_length,
            n_points=p.n_segments + 1,
            line_density=p.line_density,
            EA=p.EA,
            damping=p.damping,
            diameter=p.diameter,
            gravity=p.gravity,
            mode=p.mode,
            max_equilibrium_steps=p.max_equilibrium_steps,
            equilibrium_tol=p.equilibrium_tol,
            snapshot_interval=p.snapshot_interval,
        )

    def to_cable_params(self) -> "CableParams":
        """Convert to legacy CableParams (loses body/motion info)."""
        return CableParams(
            point_a=tuple(self.end_a_position),
            point_b=tuple(self.end_b_position),
            cable_length=self.cable_length,
            n_segments=max(0, self.n_points - 1),
            line_density=self.line_density,
            EA=self.EA,
            damping=self.damping,
            diameter=self.diameter,
            gravity=self.gravity,
            mode=self.mode,
            max_equilibrium_steps=self.max_equilibrium_steps,
            equilibrium_tol=self.equilibrium_tol,
            snapshot_interval=self.snapshot_interval,
        )

    @classmethod
    def from_cable_spec(cls, spec: "CableSpec",
                        gravity: float = 9.81,
                        mode: str = "equilibrium",
                        **solver_kwargs: Any) -> "PerCableParams":
        """Convert a CableSpec to per-cable format."""
        return cls(
            name=spec.name,
            end_a_position=tuple(spec.point_a),
            end_b_position=tuple(spec.point_b),
            cable_length=spec.cable_length,
            n_points=spec.n_points,
            line_density=spec.line_density,
            EA=spec.EA,
            damping=spec.damping,
            diameter=spec.diameter,
            gravity=gravity,
            mode=mode,
            **solver_kwargs,
        )
