cmake_minimum_required(VERSION 3.16)
project(OpenBooksNative VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(openbooks_native
    src/main.cpp
    src/storage.cpp
)

target_include_directories(openbooks_native PRIVATE src)
