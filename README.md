# c-importpath-fixer

A Python tool to automatically fix `#include "@/..."` paths in C/C++ source files by converting them to proper relative paths.

## Usage

```bash
python3 c-importpath-fixer.py [project-root]
```

By default, it scans the current directory. You can optionally pass the root of the project.

## Example

Before:

```c
#include "@/include/myheader.h"
```

After:

```c
#include "../include/myheader.h"
```

### License

MIT

Copyright 2025, Max Base
