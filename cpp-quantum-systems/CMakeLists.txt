cmake_minimum_required(VERSION 3.15)
project(QuantumTradingSystems VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler optimizations
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-O3 -march=native -ffast-math -fopenmp)
endif()

# Threading
find_package(Threads REQUIRED)
find_package(OpenMP REQUIRED)

include_directories(include)

# Monte Carlo library
add_library(monte_carlo STATIC
    src/monte_carlo/advanced_simulator.cpp
    src/monte_carlo/path_generator.cpp
    src/monte_carlo/density_estimator.cpp
    src/monte_carlo/risk_analyzer.cpp
    src/core/core_utils.cpp
)

target_link_libraries(monte_carlo Threads::Threads OpenMP::OpenMP_CXX)

# Quantum Systems library
add_library(quantum_systems STATIC
    src/quantum/dimension_manager.cpp
    src/core/core_utils.cpp
)

target_link_libraries(quantum_systems Threads::Threads OpenMP::OpenMP_CXX)

# Test executable
add_executable(test_quantum_systems tests/test_main.cpp)
target_link_libraries(test_quantum_systems monte_carlo quantum_systems)

# Python bindings (disabled for now)
option(BUILD_PYTHON_BINDINGS "Build Python bindings" OFF)
