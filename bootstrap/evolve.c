// Copyright (c) 2010 William Leszczuk
//
// Permission is hereby granted, free of charge, to any person
// obtaining a copy of this software and associated documentation
// files (the "Software"), to deal in the Software without
// restriction, including without limitation the rights to use,
// copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the
// Software is furnished to do so, subject to the following
// conditions:
//
// The above copyright notice and this permission notice shall be
// included in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
// OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
// HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
// WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
// OTHER DEALINGS IN THE SOFTWARE.

// Author: Will Leszczuk

#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define MIN(x, y) (y) > (x) ? (x) : (y)
#define BASE "python -m evolve.cli.evolvecli "

int main(int argc, char **argv) {
  char command[20 * 1024] = BASE;
  int bufindex = sizeof(BASE)-1, i = 1, result = 1;

  for (; i < argc; ++i) 
  { 
    char *singlequot;
    command[bufindex++] = '"';
    while (0 != (singlequot = strchr(argv[i], '"')))
    {
      /* TODO: inefficient, but works --------------------------------------- */
      strncpy(
        command + bufindex, 
        argv[i], 
        MIN(singlequot - argv[i] - 1, sizeof(command) - bufindex - 1)
      );
      bufindex += strlen(command + bufindex);
      /* -------------------------------------------------------------------- */
      if (bufindex >= sizeof(command) - 2) { break; }
      command[bufindex++] = '\\';
      command[bufindex++] = '"';
      argv[i] = 1 + singlequot;
    }
    /* TODO: inefficient, but works ----------------------------------------- */
    strncpy(
      command + bufindex,
      argv[i],
      sizeof(command) - bufindex - 1
    );
    bufindex += strlen(command + bufindex);
    /* ---------------------------------------------------------------------- */
    if (bufindex >= sizeof(command) - 2) { break; }
    command[bufindex++] = '"';
    command[bufindex++] = ' ';
  }

  if (bufindex >= sizeof(command)) { printf("command exceeds 20k limit\n"); }
  else
  {
    command[bufindex] = '\0';
    result = system(command);
  }

  return result;
}
