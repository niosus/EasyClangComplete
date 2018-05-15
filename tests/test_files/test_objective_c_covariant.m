#import <Foundation/Foundation.h>
@class Foo;
@interface MyCovariant<__covariant ObjectType> : NSObject
-(MyCovariant<Foo*>*)covariantMethod;
@end
