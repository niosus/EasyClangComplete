#include <Foundation/Foundation.h>
@interface Foo : NSObject
  -(NSInteger*) bar:(BOOL)b1 strParam:(NSString*)str1;
@end
int main(int argc, char const *argv[]) {
  Foo* foo = [[Foo alloc] init];
  [foo 
}
