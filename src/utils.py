from urllib.parse import unquote


def funquote(text):
    if type(text) == bytes:
        text = str(text.decode('utf-8'))
    b = ""
    while b != text:
        if b:
            text = b
        b = unquote(text)
        yield b

