#include <bar.h>

#include <stdio.h>

int main(int argc, const char *argv[])
{
	printf("%s: %d\n", argv[0], bar(argv[0]));
	return 0;
}
