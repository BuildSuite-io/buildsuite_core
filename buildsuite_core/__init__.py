__version__ = "0.0.1"

def to_camel_case(sentence):
    words = sentence.split()
    camel_case = "".join([words[0].lower()] + [word.capitalize() for word in words[1:]])
    return camel_case


from buildsuite_core.workflow import apply_patches

apply_patches()