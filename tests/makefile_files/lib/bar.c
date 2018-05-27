#include <foo.h>
#include <string.h>

int bar(const char *str)
{
	return foo(strlen(str), 3);
}
