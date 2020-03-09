// Test program to check system includes in YCM semantic completion.
// See https://github.com/grailbio/bazel-compilation-database/issues/36

#include <cstddef>
#include <ctime>
#include <iostream>

int main() {
  std::time_t result = std::time(nullptr);
  std::cout << std::asctime(std::localtime(&result));
  return 0;
}
