import sys

# The wrapper must not write inside the working tree, which it runs from. Only `python -B` keeps this file's
# own bytecode out of it, since Python caches it before running it.
sys.dont_write_bytecode = True

from sdlc_evals.cli import main  # noqa: E402

sys.exit(main())
