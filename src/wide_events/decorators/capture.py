

def never_capture():
    def mark(v):
        setattr(v, "capture", False)
        return v
    return mark