cmake_minimum_required(VERSION 3.20)
project(SynapticContinuum_EXP0004 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MSVC)
    add_compile_options(/O2 /W4 /permissive-)
else()
    add_compile_options(-O3 -Wall -Wextra -Wpedantic -pthread)
endif()

# Include directories: local src/cpp and EXP-0003 core headers
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../EXP-0003-native-engine-scaling/src/cpp
)

# Test Executable
add_executable(topology_tests
    src/cpp/tests/topology_tests.cpp
)
target_link_libraries(topology_tests PRIVATE pthread)

# Benchmark Executable
add_executable(exp0004_bench
    src/cpp/benchmarks/exp0004_bench.cpp
)
target_link_libraries(exp0004_bench PRIVATE pthread)

# Output directory
set_target_properties(topology_tests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
)
set_target_properties(exp0004_bench PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin"
)
