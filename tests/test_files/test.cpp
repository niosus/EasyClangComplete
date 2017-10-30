class A {
  int a;
  void foo(int a);
public:
  void foo(double a);
};
int main(int argc, char const *argv[]) {
  A a;
  return 0;
}
