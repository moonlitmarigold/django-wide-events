

def never_capture(v):
    setattr(v, "capture", False)
    return v

def always_capture(v):
    setattr(v, "capture", True)
    return v