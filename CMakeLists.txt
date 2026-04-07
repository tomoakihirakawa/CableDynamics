# ==========================================================================
# Cable Dynamics — Mooring Line Dynamics Solver
# ==========================================================================
cmake_minimum_required(VERSION 3.16)

# --- Compiler selection ---
set(BEM_COMPILER "gcc" CACHE STRING "Select compiler toolchain: gcc or clang")
set_property(CACHE BEM_COMPILER PROPERTY STRINGS "gcc" "clang")
option(BEM_ENABLE_OPENMP "Enable OpenMP parallelization" ON)

set(_BEM_DISABLE_FLOAT128_DEFAULT OFF)
if(BEM_COMPILER STREQUAL "clang")
  set(_BEM_DISABLE_FLOAT128_DEFAULT ON)
endif()
option(BEM_DISABLE_FLOAT128 "Disable std::float128_t / quadmath codepaths" ${_BEM_DISABLE_FLOAT128_DEFAULT})

# --- Compiler detection ---
if(NOT DEFINED CMAKE_CXX_COMPILER OR CMAKE_CXX_COMPILER STREQUAL "")
  if(BEM_COMPILER STREQUAL "gcc")
    foreach(ver IN ITEMS 15 14 13 12)
      find_program(_BEM_GXX NAMES "g++-${ver}")
      if(_BEM_GXX)
        set(CMAKE_CXX_COMPILER "${_BEM_GXX}" CACHE FILEPATH "C++ compiler" FORCE)
        break()
      endif()
    endforeach()
    if(NOT CMAKE_CXX_COMPILER)
      message(FATAL_ERROR "No suitable g++ found.")
    endif()
  elseif(BEM_COMPILER STREQUAL "clang")
    find_program(_BEM_CLANGXX NAMES "clang++"
      PATHS "/opt/homebrew/opt/llvm/bin" "/usr/local/opt/llvm/bin" NO_DEFAULT_PATH)
    if(NOT _BEM_CLANGXX)
      find_program(_BEM_CLANGXX NAMES "clang++")
    endif()
    if(NOT _BEM_CLANGXX)
      message(FATAL_ERROR "clang++ not found.")
    endif()
    set(CMAKE_CXX_COMPILER "${_BEM_CLANGXX}" CACHE FILEPATH "C++ compiler" FORCE)
  endif()
endif()

project(CableDynamics CXX)

# --- Build type ---
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# --- Project settings ---
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

find_program(CCACHE_EXE ccache)
if(CCACHE_EXE)
  set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_EXE}")
endif()

# --- Sources ---
add_executable(cable_solver
    "${PROJECT_SOURCE_DIR}/cable/cable_solver.cpp"
    "${PROJECT_SOURCE_DIR}/lib/src/Network.cpp"
    "${PROJECT_SOURCE_DIR}/lib/src/networkPoint.cpp"
    "${PROJECT_SOURCE_DIR}/lib/src/networkLine.cpp"
    "${PROJECT_SOURCE_DIR}/lib/src/networkFace.cpp"
    "${PROJECT_SOURCE_DIR}/lib/src/networkTetra.cpp"
)

# --- Includes ---
target_include_directories(cable_solver PUBLIC
    "${PROJECT_SOURCE_DIR}/lib/include"
)

# --- Compile options ---
target_compile_options(cable_solver PRIVATE
    -march=native -funroll-loops -pthread
    $<$<CXX_COMPILER_ID:GNU>:-fconcepts>
    $<$<CONFIG:RELEASE>:-O3>
    $<$<CONFIG:DEBUG>:-Og>
)

# --- OpenMP ---
if(BEM_ENABLE_OPENMP)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(cable_solver PRIVATE -fopenmp)
    target_link_libraries(cable_solver PRIVATE gomp)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    find_package(OpenMP QUIET)
    if(OpenMP_CXX_FOUND)
      target_link_libraries(cable_solver PRIVATE OpenMP::OpenMP_CXX)
    else()
      find_path(BEM_OMP_INC omp.h PATHS "/opt/homebrew/opt/libomp/include" "/usr/local/opt/libomp/include")
      find_library(BEM_OMP_LIB NAMES omp PATHS "/opt/homebrew/opt/libomp/lib" "/usr/local/opt/libomp/lib")
      if(BEM_OMP_INC AND BEM_OMP_LIB)
        target_compile_options(cable_solver PRIVATE -Xpreprocessor -fopenmp)
        target_include_directories(cable_solver PRIVATE "${BEM_OMP_INC}")
        target_link_libraries(cable_solver PRIVATE "${BEM_OMP_LIB}")
      endif()
    endif()
  endif()
endif()

# --- Libraries ---
target_link_libraries(cable_solver PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:quadmath>
    lapack blas
)

message(STATUS "")
message(STATUS "Build: mkdir build && cd build && cmake .. && make -j$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)")
message(STATUS "")
