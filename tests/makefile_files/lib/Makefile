CFLAGS = -Ifoo
CPPFLAGS = -DREQUIRED_DEFINE
CC = clang
AR = ar

libbar.a :	bar.o foo.o
			$(AR) rcs $@ $?

foo.o :		foo/foo.h foo/foo.c
			$(CC) $(CFLAGS) -c -o $@ foo/foo.c

bar.o :		bar.c
			$(CC) $(CFLAGS) -c -o $@ bar.c

clean :
			rm *.o *.a
