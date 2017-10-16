/// Just a helper file for manually viewing and testing macro tooltips

void foo();

#define MACRO_01
#define MACRO_02 \

#define MACRO_03 \
                 foo();


#define MACRO_04 foo();
#define MACRO_05 foo(); \

#define MACRO_06 foo(); \
                 foo();
#define MACRO_07 \
                 foo();

#define MACRO_08() foo()
#define MACRO_09() foo() \

#define MACRO_10() foo(); \
                   foo()
#define MACRO_11() \
                   foo()

#define MACRO_12( \
                )
#define MACRO_13( \
                ) foo()
int main()
{
    MACRO_01;
    MACRO_02;
    MACRO_03;
    MACRO_04;
    MACRO_05;
    MACRO_06;
    MACRO_07;
    MACRO_08();
    MACRO_09();
    MACRO_10();
    MACRO_11();
    MACRO_12();
    MACRO_13();
}
