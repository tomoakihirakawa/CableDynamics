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

```bash
./cable_solver path/to/cable_config.json
```

## Directory Structure

```
├── lib/                  # Shared library (mesh, geometry)
│   ├── include/          # Header files
│   └── src/              # Source files
└── cable/                # Cable dynamics solver
```

## Related Packages

- [BEM_TimeDomain](https://github.com/tomoakihirakawa/BEM_TimeDomain) — Time-domain nonlinear BEM
- [BEM_FreqDomain](https://github.com/tomoakihirakawa/BEM_FreqDomain) — Frequency-domain BEM
- [BEM_for_Nonlinear_Waves](https://github.com/tomoakihirakawa/BEM_for_Nonlinear_Waves) — Integrated repository

## License

LGPL-3.0-or-later. See [LICENSE](LICENSE).
