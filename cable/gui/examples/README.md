# Example input files

These JSON files are valid input for both the C++ `cable_solver` CLI and
the pycable GUI. They exercise the equilibrium solver in two regimes —
deep-sea mooring scale and bridge cable scale.

## Files

| File | Scenario |
|---|---|
| `catenary_500m.json` | Mooring-chain scale: 500 m horizontal span, 58 m depth, heavy chain. Matches the defaults in `cable/cable_solver.cpp`. |
| `bridge_cable_small.json` | Bridge-cable scale: 50 m horizontal span, 5 m height drop, light steel strand. |

## Parameter reference

All keys map 1:1 to `cable_solver` input. See
[`cable/cable_solver.cpp`](../../cable/cable_solver.cpp) for the
authoritative parser.

| Key | Unit | Meaning |
|---|---|---|
| `point_a` | `[x, y, z]` in metres | First anchor (typically seabed anchor for mooring, tower top for bridges) |
| `point_b` | `[x, y, z]` in metres | Second anchor (typically fairlead / deck attachment) |
| `cable_length` | m | Unstretched total length. Must be ≥ straight-line distance between A and B or the cable cannot hang slack. |
| `n_segments` | — | Number of lumped-mass segments. Typical 20–100. Higher = smoother catenary, slower solve. |
| `line_density` | kg/m | Mass per unit length including any weight correction (e.g. submerged weight for mooring). |
| `EA` | N | Axial stiffness (Young's modulus × cross-section). Steel strand ≈ 2e9 N. Mooring chain ≈ 1.4e9 N. |
| `damping` | — | Artificial relaxation coefficient used only by equilibrium mode. 0.5 is a good default. Not a physical damping. |
| `diameter` | m | Effective hydrodynamic diameter (drag force uses it). For mooring in water this sets the drag scale. |
| `gravity` | m/s² | Set to 9.81 for Earth surface. |
| `mode` | string | Currently only `"equilibrium"` is supported by the solver. |
| `max_equilibrium_steps` | — | Cap on RK4 iterations. Realistic equilibrium cases converge in hundreds to thousands of steps, so 500 000 is a very loose ceiling. |
| `equilibrium_tol` | m/s | Stop when `max_|v| < equilibrium_tol` after at least 1000 warm-up steps. |
| `snapshot_interval` | — | Emit one `SNAPSHOT` stdout line every N steps for live GUI animation. |

## Typical value ranges

| Quantity | Offshore mooring | Bridge cable |
|---|---|---|
| Span | 100–2000 m | 10–500 m |
| Depth / height | 50–3000 m | 2–100 m |
| Line density | 100–500 kg/m (chain), 10–30 kg/m (rope) | 30–150 kg/m (locked-coil strand) |
| EA | 1e8 – 2e9 N | 1e9 – 5e9 N |
| Diameter | 0.05 – 0.3 m | 0.02 – 0.15 m |

## Running

Direct CLI (works from either dev or public tree; `cable_solver` must
already be built):

```bash
# Dev tree
cd <cpp>/cable/build_solver
./cable_solver ../gui/examples/catenary_500m.json /tmp/cable_out/

# Public tree
cd ~/CableDynamics
./build/cable_solver cable/gui/examples/catenary_500m.json /tmp/cable_out/

cat /tmp/cable_out/result.json | python -m json.tool | head
```

Or via the pycable GUI:

```bash
cd <cpp>/cable/gui        # or ~/CableDynamics/cable/gui
./run.sh
# File → Open… is not yet implemented; the defaults in the form already
# match catenary_500m.json. Just click Run.
```
