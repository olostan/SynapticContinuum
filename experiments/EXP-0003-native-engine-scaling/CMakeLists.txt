cmake_minimum_required(VERSION 3.20)
project(SynapticContinuum_NativeEngine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Optimization and warning flags
if(MSVC)
    add_compile_options(/O2 /W4 /permissive-)
else()
    add_compile_options(-O3 -Wall -Wextra -Wpedantic -pthread)
    # Portable performance: avoid non-portable arch flags to ensure Apple Silicon and Linux x86 portability
    if(NOT APPLE AND NOT WIN32)
        # Enable SSE/AVX where supported on x86, but keep fallback portable
    endif()
endif()

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp
)

# CLI Executable
add_executable(sc_engine
    src/cpp/cli/sc_engine_cli.cpp
)
target_link_libraries(sc_engine PRIVATE pthread)

# Unit Test Executable
add_executable(sc_tests
    src/cpp/tests/sc_tests.cpp
)
target_link_libraries(sc_tests PRIVATE pthread)

# Fidelity Sweep Benchmark Executable
add_executable(fidelity_sweep
    src/cpp/benchmarks/fidelity_sweep.cpp
)
target_link_libraries(fidelity_sweep PRIVATE pthread)

# Output directories
set_target_properties(sc_engine PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
)
set_target_properties(sc_tests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
)
set_target_properties(fidelity_sweep PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
)
