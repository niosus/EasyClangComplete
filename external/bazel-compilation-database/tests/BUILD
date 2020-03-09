# Copyright 2017 GRAIL, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")

cc_library(
    name = "A",
    srcs = ["a.cc"],
    hdrs = ["a.h"],
)

cc_library(
    name = "B",
    srcs = ["b.cc"],
    deps = [":A"],
)

cc_binary(
    name = "stdlib",
    srcs = ["stdlib.cc"],
)

load("@compdb//:aspects.bzl", "compilation_database")

compilation_database(
    name = "compdb",
    exec_root = "bazel-tests",
    targets = ["B"],
)
