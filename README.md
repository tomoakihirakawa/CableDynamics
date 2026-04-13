# Cable Dynamics

Mooring line dynamics solver using a lumped-mass approach with
leapfrog time integration.

## Features

- Lumped-mass mooring line model
- Leapfrog time integration
- Nonlinear axial stiffness
- Seabed contact
- JSON-based input files
- VTK output for visualization

## Build

Requires: C++23 compiler (GCC 12+ or Clang 16+), CMake 3.16+, LAPACK/BLAS.

```bash
mkdir build && cd build
cmake ..
make -j$(sysctl -n hw.logicalcpu)    # macOS
make -j$(nproc)                       # Linux
```

## Usage

### C++ CLI

```bash
./build/cable_solver input.json output_dir/
```

Two arguments are required: an input JSON file (see
[`cable/gui/examples/`](cable/gui/examples/) for working samples) and an
output directory where `result.json` and per-snapshot data are written.

### Python GUI

A PySide6 / PyVista GUI that drives the same `cable_solver` binary lives in
[`cable/gui/`](cable/gui/). It exposes a parameter form, launches the solver,
shows live convergence in 3D, and colors the final cable by tension. See
[`cable/gui/README.md`](cable/gui/README.md) for setup and usage.

```bash
cd cable/gui
./run.sh
```

## Directory Structure

```
├── lib/                   # Shared library (mesh, geometry)
│   ├── include/           # Header files
│   └── src/               # Source files
└── cable/                 # Cable dynamics solver
    ├── cable_solver.cpp   # C++ entry point
    └── gui/               # Python GUI wrapper (pycable) — optional
        ├── pycable/
        ├── examples/
        └── tests/
```

## Related Packages

- [BEM_TimeDomain](https://github.com/tomoakihirakawa/BEM_TimeDomain) — Time-domain nonlinear BEM
- [BEM_FreqDomain](https://github.com/tomoakihirakawa/BEM_FreqDomain) — Frequency-domain BEM
- [BEM_for_Nonlinear_Waves](https://github.com/tomoakihirakawa/BEM_for_Nonlinear_Waves) — Integrated repository

## License

LGPL-3.0-or-later. See [LICENSE](LICENSE).
