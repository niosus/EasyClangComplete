//------------------------------------------------------------------------------
/// @brief      Class for my cool class.
///
class MyCoolClass {
 public:
  /**
   * @brief      This is short.
   *
   *             And this is a full comment.
   *
   * @param[in]  a     param a
   * @param[in]  b     param b
   */
  void foo(int a, int b);
};

int main(int argc, char const *argv[]) {
  MyCoolClass cool_class;
  cool_class.foo(2, 2);
  return 0;
}
