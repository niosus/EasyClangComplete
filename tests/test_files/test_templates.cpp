class Foo;
template <class TClass=Foo, typename TType=int, int TInt=12>
class TemplateClass
{
public:
  void foo(TemplateClass<TClass, TType, TInt>);
};
int main(int argc, char const *argv[]) {
  TemplateClass<Foo, int, 123> instanceClassTypeInt;
  TemplateClass<Foo> instanceClassAndDefaults;
  TemplateClass<TemplateClass<Foo>> instanceNested;
  TemplateClass<Foo*> instancePointer;
  TemplateClass<Foo&> instanceRef;
  TemplateClass<Foo&&> instanceRValueRef;
  instanceRValueRef.foo(instanceRValueRef);
  return 0;
}
