INCLUDES = -Iinc
CPPFLAGS = -DREQUIRED_DEFINE
CC = clang

app :	main.c inc/bar.h
		$(MAKE) -C lib
		$(CC) $(INCLUDES) $(CPPFLAGS) -o $@ main.c lib/libbar.a

clean :
		$(MAKE) -C lib clean
		rm app
