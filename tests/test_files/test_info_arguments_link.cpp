class Foo {};

class MyCoolClass {
 public:
  void foo(Foo a, Foo* b);
};

int main(int argc, char const *argv[]) {
  MyCoolClass cool_class;
  cool_class.foo(Foo(), nullptr);
  return 0;
}
