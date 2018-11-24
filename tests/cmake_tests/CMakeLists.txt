cmake_minimum_required(VERSION 2.8)

project (test_cmake_project)

add_subdirectory(lib)
include_directories(lib)

add_executable(test_a test_a.cpp)
target_link_libraries(test_a liba)
