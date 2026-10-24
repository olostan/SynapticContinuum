cmake_minimum_required(VERSION 3.20)
project(SynapticContinuum_EXP0004 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Threads REQUIRED)
find_package(OpenMP)
include(CheckCXXCompilerFlag)

# Common compiler warnings
if(MSVC)
    set(SC_COMMON_FLAGS /W4 /permissive-)
    set(SC_RELEASE_FLAGS /O2 /DNDEBUG)
else()
    set(SC_COMMON_FLAGS -Wall -Wextra -Wpedantic)
    set(SC_RELEASE_FLAGS -O3 -DNDEBUG)
endif()

# Check for CPU-specific optimization flags (Zen3 on x86_64, Apple M-series on Darwin ARM64)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    check_cxx_compiler_flag("-march=znver3 -mtune=znver3" COMPILER_SUPPORTS_ZNVER3)
    if(COMPILER_SUPPORTS_ZNVER3)
        set(SC_NATIVE_FLAGS -O3 -march=znver3 -mtune=znver3 -DNDEBUG)
        message(STATUS "Architecture-specific tuning enabled: -march=znver3 -mtune=znver3 supported")
    else()
        set(SC_NATIVE_FLAGS -O3 -DNDEBUG)
    endif()
elseif(APPLE AND CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    check_cxx_compiler_flag("-mcpu=apple-m4" COMPILER_SUPPORTS_APPLE_M4)
    check_cxx_compiler_flag("-mcpu=native" COMPILER_SUPPORTS_MCPU_NATIVE)
    if(COMPILER_SUPPORTS_APPLE_M4)
        set(SC_NATIVE_FLAGS -O3 -mcpu=apple-m4 -DNDEBUG)
        message(STATUS "Architecture-specific tuning enabled: -mcpu=apple-m4 supported")
    elseif(COMPILER_SUPPORTS_MCPU_NATIVE)
        set(SC_NATIVE_FLAGS -O3 -mcpu=native -DNDEBUG)
        message(STATUS "Architecture-specific tuning enabled: -mcpu=native supported")
    else()
        set(SC_NATIVE_FLAGS -O3 -DNDEBUG)
    endif()
else()
    set(SC_NATIVE_FLAGS -O3 -DNDEBUG)
endif()

# Pass git commit hash for source provenance
execute_process(
    COMMAND git rev-parse --short HEAD
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE SC_GIT_COMMIT_SHA
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(NOT SC_GIT_COMMIT_SHA)
    set(SC_GIT_COMMIT_SHA "unknown")
endif()
add_compile_definitions(SC_GIT_COMMIT_SHA="${SC_GIT_COMMIT_SHA}")

# Interface library for shared includes
add_library(exp0004_common INTERFACE)
target_include_directories(exp0004_common INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../EXP-0003-native-engine-scaling/src/cpp
)
target_compile_options(exp0004_common INTERFACE ${SC_COMMON_FLAGS})

# 1. Standard Release Test Executable
add_executable(topology_tests src/cpp/tests/topology_tests.cpp)
target_link_libraries(topology_tests PRIVATE exp0004_common Threads::Threads)
if(OpenMP_CXX_FOUND)
    target_link_libraries(topology_tests PRIVATE OpenMP::OpenMP_CXX)
endif()
target_compile_options(topology_tests PRIVATE ${SC_RELEASE_FLAGS})

# 2. AddressSanitizer + UBSan Test Executable
if(NOT MSVC)
    add_executable(topology_tests_asan src/cpp/tests/topology_tests.cpp)
    target_link_libraries(topology_tests_asan PRIVATE exp0004_common Threads::Threads)
    if(OpenMP_CXX_FOUND)
        target_link_libraries(topology_tests_asan PRIVATE OpenMP::OpenMP_CXX)
    endif()
    target_compile_options(topology_tests_asan PRIVATE -fsanitize=address,undefined -g -O1)
    target_link_options(topology_tests_asan PRIVATE -fsanitize=address,undefined)

    # 3. ThreadSanitizer Test Executable (Note: libgomp is uninstrumented by TSan on GCC/Linux, so OpenMP is omitted from the TSan target)
    add_executable(topology_tests_tsan src/cpp/tests/topology_tests.cpp)
    target_link_libraries(topology_tests_tsan PRIVATE exp0004_common Threads::Threads)
    target_compile_options(topology_tests_tsan PRIVATE -fsanitize=thread -g -O1)
    target_link_options(topology_tests_tsan PRIVATE -fsanitize=thread)
endif()

# 4. Standard Portable Benchmark Executable (-O3)
add_executable(exp0004_bench src/cpp/benchmarks/exp0004_bench.cpp)
target_link_libraries(exp0004_bench PRIVATE exp0004_common Threads::Threads)
if(OpenMP_CXX_FOUND)
    target_link_libraries(exp0004_bench PRIVATE OpenMP::OpenMP_CXX)
endif()
target_compile_options(exp0004_bench PRIVATE ${SC_RELEASE_FLAGS})

# 5. Native Tuned Benchmark Executable (Zen3)
add_executable(exp0004_bench_native src/cpp/benchmarks/exp0004_bench.cpp)
target_link_libraries(exp0004_bench_native PRIVATE exp0004_common Threads::Threads)
if(OpenMP_CXX_FOUND)
    target_link_libraries(exp0004_bench_native PRIVATE OpenMP::OpenMP_CXX)
endif()
target_compile_options(exp0004_bench_native PRIVATE ${SC_NATIVE_FLAGS})

# Runtime output directory
set_target_properties(topology_tests PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
set_target_properties(exp0004_bench PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
set_target_properties(exp0004_bench_native PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
if(NOT MSVC)
    set_target_properties(topology_tests_asan PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
    set_target_properties(topology_tests_tsan PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
endif()
