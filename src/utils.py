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

def readconfs(config):
    with open(config, 'r') as fd:
        data = fd.read()
    blocnumber = data.count('[')
    parsed_bloc = {}
    for bloc in range(blocnumber):
        # bloc is an index
        parsed_var = {}
        current_bloc = data.split('[')[bloc+1]
        current_bloc = current_bloc.replace(' ','')
        btype = current_bloc.split(']')[0]
        for line in current_bloc.split('\n')[1:]:
            if len(line) == 0 or '#' in line:
                # empty line. probably for readability
                pass
            else:
                var_name, var_value = line.split('=')
                parsed_var[var_name] = var_value
        parsed_bloc[btype] = parsed_var
    return parsed_bloc



if __name__ == '__main__':
    main()

