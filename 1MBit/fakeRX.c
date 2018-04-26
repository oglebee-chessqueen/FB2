#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

// compile: gcc fakeRX.c -o fakeRX
// usage:
//   takes one optional command line argument for maximum filesize to output
//   input one character at a time to stdin
//     if q, quit
//     if w, write bytes until max filesize is reached
//     else print input+1

int main(int argc, char **argv)
{
	char *filename = "./test.dat";
	unsigned int maxsize = 10000; // 100 MB
	if (argc >= 2)
		maxsize = atoi(argv[1]);
	FILE *fp;
	unsigned int i;
	char c;
	while (1)
	{
		scanf("%s", &c);
		if (c == 'q')
			break;
		else if (c == 'w')
		{
			printf("maxsize: %d\n", maxsize);
			fp = fopen(filename, "w");
			for (i = 0; i < maxsize; i++)
				fprintf(fp, "%c", i);
			fclose(fp);
		}
		else
			printf("%c\n", c + 1);
		c = 0;
	}

	return 0;
}
