

def always_trace(v):
    setattr(v, "trace", True)
    return v

def never_trace(v):
    setattr(v, "trace", False)
    return v
