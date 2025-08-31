# Minimal helper placeholder in case other modules import it later.
def print_verbose(verbose: bool, *args, **kwargs):
    if verbose:
        print(*args, **kwargs, flush=True)
