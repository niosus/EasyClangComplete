/// File using several C++ libraries with templated types,
/// useful for manual testing of popup info by hovering over code.
/// Not added to auto-testing because popups include
/// libC++ implementation details that can change without warning,
/// making it difficult to test for correct info in the popups.
#include <algorithm>
#include <array>
#include <functional>
#include <memory>
#include <string>
#include <utility>
class A {
  int a;
  void foo(int a);
public:
  void foo(double a);

  template<int BarTemplateParameter>
  int bar() { return BarTemplateParameter;}

  template<class One, class Two, class Three>
  void barTemp3();

  template<int M>
  int barM(std::shared_ptr<A> a, const std::shared_ptr<A>& aConst) { return M;}

  std::shared_ptr<A>& barNoTempl(
    std::shared_ptr<A> sharedPtr,
    const std::shared_ptr<A>& constRefToSharedPtr,
    std::shared_ptr<A>&& rValueRefToSharedPtr);
};


template <typename TempArg>
class Templated {
};

template <typename TempArg1, typename TempArg2>
class TemplatedTwo {
};

int main(int argc, char const *argv[]) {
  std::shared_ptr<A> pointerToA;
  pointerToA.reset();
  pointerToA->bar<5>();
  pointerToA->barTemp3<A, A, A>();
  pointerToA->barM<5>(pointerToA, pointerToA);
  pointerToA.reset(pointerToA.get());
  std::pair<std::shared_ptr<A>, std::string> myPair;
  myPair.first = nullptr;

  A justA;
  A& refA = justA;
  A* ptrA;
  A*& ptrRefA = ptrA;
  A&& rvalueRefA = std::move(justA);
  Templated<int> templatedInt;
  Templated<A> templatedA;
  Templated<A&&> templatedOnARvalueRef;
  Templated<std::shared_ptr<const A&&>*>* templatedSharedPtrARvalueRef;
  Templated<A>&& templatedARValueRef = std::move(templatedA);
  Templated<A*> templatedAPtr;
  Templated<A*>& templatedAPtrRef = templatedAPtr;
  Templated<std::shared_ptr<A*>> templatedSharedPtrAPtr;
  Templated<const std::shared_ptr<A*>> templatedConstSharedPtrAPtr;
  Templated<const std::shared_ptr<A>*>* templatedConstSharedPtrAPtrPtr;
  Templated<std::shared_ptr<A>> templatedSharedPtrA;
  Templated<std::shared_ptr<const A>> templatedSharedPtrConstA;
  Templated<const std::shared_ptr<const A>> templatedConstSharedPtrConstA;

  TemplatedTwo<A, A> templatedTwoAA;
  TemplatedTwo<std::shared_ptr<const A>, const std::shared_ptr<A>*> templatedTwoSharedConstA_ConstSharedPtrPointer;
  A a;
  a.foo(2.0);

  std::array<A, 5> arraySize5;

  auto lambda = [](std::shared_ptr<A> a) {
    return a;
  };
  lambda(pointerToA);
  return 0;
}
