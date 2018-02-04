// A bunch of different types of protocols/methods

#import <Foundation/Foundation.h>
#import <Foundation/NSString.h>

@class Foo;

@protocol Protocol
  -(void)protocolMethodVoidNoParameters; ///< Has a brief comment
  -(BOOL)protocolMethodBoolNoParameters;
  -(void)protocolMethodVoidOneStringParameter:(NSString*)s1;
  -(void)protocolMethodVoidTwoStringParameters:(NSString*)s1
    stringParam2:(NSString*)s2;
  +(void)protocolClassMethod;
  @property (assign) BOOL protocolPropertyBool;
@end

@interface Interface : NSObject<Protocol>
  -(void)interfaceMethodVoidNoParameters; ///< Brief comment.
  -(BOOL)interfaceMethodBoolNoParameters;
  -(void)interfaceMethodVoidOneStringParameter:(NSString*)s1;
  -(void)interfaceMethodVoidTwoStringParameters:(NSString*)s1
    stringParam2:(NSString*)s2;
  -(void)interfaceMethodVoidTwoParametersSecondUnnamed:(int)int1
    :(int)int2;
  +(Foo*)interfaceClassMethodFooTwoFooParameters:(Foo*)f1
    fooParam2:(Foo*)f2;
  @property (assign) NSString* interfacePropertyString;
@end

@implementation Interface
  @synthesize protocolPropertyBool;

  -(void)interfaceMethodVoidNoParameters {}
  -(BOOL)interfaceMethodBoolNoParameters { return YES; }
  -(void)interfaceMethodVoidOneStringParameter:(NSString*)s1 {}
  -(void)interfaceMethodVoidTwoStringParameters:(NSString*)s1
    stringParam2:(NSString*)s2 {}
  -(void)interfaceMethodVoidTwoParametersSecondUnnamed:(int)int1
    :(int)int2 {}
  +(Foo*)interfaceClassMethodFooTwoFooParameters:(Foo*)f1
    fooParam2:(Foo*)f2 { return nil; }

  -(void)protocolMethodVoidNoParameters {}
  -(BOOL)protocolMethodBoolNoParameters { return YES; }
  -(void)protocolMethodVoidOneStringParameter:(NSString*)s1 {}
  -(void)protocolMethodVoidTwoStringParameters:(NSString*)s1
    stringParam2:(NSString*)s2 {}
  +(void)protocolClassMethod {}

@end

@interface Interface (Category)
  -(void)categoryMethodVoidNoParameters;
@end

@implementation Interface (Category)
  -(void)categoryMethodVoidNoParameters{}
@end

/// Just a bunch of calls used to help manually test tooltip popups
int main(int argc, const char * argv[])
{
  Interface* interface = [[Interface alloc] init];

  [interface interfaceMethodVoidNoParameters];
  [interface interfaceMethodBoolNoParameters];
  [interface interfaceMethodVoidOneStringParameter:nil];
  [interface interfaceMethodVoidTwoStringParameters:nil stringParam2:nil];
  [interface interfaceMethodVoidTwoParametersSecondUnnamed:0 :0];
  [Interface interfaceClassMethodFooTwoFooParameters:nil fooParam2:nil];
  interface.interfacePropertyString = nil;

  [interface protocolMethodVoidNoParameters];
  [interface protocolMethodBoolNoParameters];
  [interface protocolMethodVoidOneStringParameter:nil];
  [interface protocolMethodVoidTwoStringParameters:nil stringParam2:nil];
  [Interface protocolClassMethod];
  interface.protocolPropertyBool = YES;

  [interface categoryMethodVoidNoParameters];

  [interface performSelector:@selector(interfaceMethodVoidNoParameters)];

  id<Protocol> protocol = nil;
  [protocol protocolMethodVoidNoParameters];
  [protocol protocolMethodBoolNoParameters];
  [protocol protocolMethodVoidOneStringParameter:nil];
  [protocol protocolMethodVoidTwoStringParameters:nil stringParam2:nil];

  interface.
  NSLog(@"Hello world");

  return 0;
}

