def can_build(env, platform):
    return platform == "switch" and env["precision"] == "double"

def configure(env):
    pass
