from flask import Flask, request, render_template_string
import re
import ply.lex as lex

app = Flask(__name__)

# Definición de tokens para el analizador léxico
tokens = [
    'KEYWORD', 'ID', 'NUM', 'SYM', 'ERR'
]

t_KEYWORD = r'\b(int|DO|ENDDO|WHILE|ENDWHILE)\b'
t_ID = r'\b[a-zA-Z_][a-zA-Z_0-9]*\b'
t_NUM = r'\b\d+\b'
t_SYM = r'[;=()*+-]'
t_ERR = r'.'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Carácter ilegal '{t.value[0]}'")
    t.lexer.skip(1)

# Plantilla HTML para mostrar resultados
html_template = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <style>
                .contenedor {
                    width: 100%;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: #fff;
                }
                h1 {
                    color: #333;
                }
                textarea {
                    width: 100%;
                    height: 200px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                    font-size: 16px;
                }
                input[type="submit"] {
                    background-color: #007BFF;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 18px;
                }
                input[type="submit"]:hover {
                    background-color: #0056b3;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-size: 16px;
                }
                .error {
                    color: red;
                    font-weight: bold;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }
                th {
                    background-color: #f2f2f2;
                    color: #333;
                }
            </style>
  <title>Analizador de Pseudocódigo</title>
</head>
<body>
  <div class="container">
    <h1>Analizador de Pseudocódigo</h1>
    <form method="post">
      <textarea name="code" rows="10" cols="50">{{ code }}</textarea><br>
      <input type="submit" value="Analizar">
    </form>
    <div>
      <h2>Analizador Léxico</h2>
      <table>
        <tr>
          <th>Tokens</th><th>KEYWORD</th><th>ID</th><th>Números</th><th>Símbolos</th><th>Error</th>
        </tr>
        {% for row in lexical %}
        <tr>
          <td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td><td>{{ row[4] }}</td><td>{{ row[5] }}</td>
        </tr>
        {% endfor %}
        <tr>
          <td>Total</td><td>{{ total['KEYWORD'] }}</td><td>{{ total['ID'] }}</td><td>{{ total['NUM'] }}</td><td>{{ total['SYM'] }}</td><td>{{ total['ERR'] }}</td>
        </tr>
      </table>
    </div>
    <div>
      <h2>Analizador Sintáctico y Semántico</h2>
      <table>
        <tr>
          <th>Sintáctico</th><th>Semántico</th>
        </tr>
        <tr>
          <td>{{ syntactic }}</td><td>{{ semantic }}</td>
        </tr>
      </table>
    </div>
  </div>
</body>
</html>
'''

def analyze_lexical(code):
    lexer = lex.lex()
    lexer.input(code)
    results = {'KEYWORD': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    rows = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        row = [''] * 6
        if tok.type in results:
            results[tok.type] += 1
            row[list(results.keys()).index(tok.type)] = 'x'
        rows.append(row)
    return rows, results

def analyze_syntactic(code):
    errors = []
    do_count = 0
    while_count = 0
    within_do_block = False
    operation_in_block = False

    lines = code.split('\n')
    for i, line in enumerate(lines):
        stripped_line = line.strip()

        # Verificar la estructura básica de DO...ENDDO
        if stripped_line == 'DO':
            do_count += 1
            within_do_block = True
            operation_in_block = False
        elif stripped_line == 'ENDDO':
            if do_count <= 0:
                errors.append(f"ENDDO sin correspondiente DO en la línea {i + 1}.")
            else:
                do_count -= 1
            if not operation_in_block:
                errors.append(f"Bloque DO...ENDDO sin operaciones básicas en la línea {i + 1}.")
            within_do_block = False

        # Verificar que dentro de DO...ENDDO haya al menos una operación que termine con ;
        elif within_do_block and stripped_line and not stripped_line.startswith('DO') and not stripped_line.startswith('ENDDO'):
            if re.search(r'[+\-*/]', stripped_line) and stripped_line.endswith(';'):
                operation_in_block = True
            if not re.search(r'[+\-*/]', stripped_line):
                errors.append(f"Falta una operación básica en la línea {i + 1}: {line}")
            elif not stripped_line.endswith(';'):
                errors.append(f"Falta ; al final de la línea {i + 1}: {line}")

        # Verificar la estructura básica de WHILE...ENDWHILE
        elif stripped_line.startswith('WHILE'):
            while_count += 1
            if stripped_line.count('(') != stripped_line.count(')'):
                errors.append(f"Desbalance de paréntesis en la línea {i + 1}: {line}")
            # Verificar que la condición en el WHILE sea del tipo int
            condition = re.search(r'\((.*?)\)', stripped_line)
            if condition:
                condition = condition.group(1).strip()
                if not re.match(r'int\s+[a-zA-Z_][a-zA-Z_0-9]*\s*==\s*\d+', condition):
                    errors.append(f"Condición en WHILE debe ser de tipo int en la línea {i + 1}: {line}")
        elif stripped_line == 'ENDWHILE':
            if while_count <= 0:
                errors.append(f"ENDWHILE sin correspondiente WHILE en la línea {i + 1}.")
            else:
                while_count -= 1

        # Verificar la declaración de variables con punto y coma
        elif re.match(r'\bint\s+[a-zA-Z_][a-zA-Z_0-9]*\s*=\s*\d+\s*;', stripped_line):
            pass
        elif 'int' in stripped_line and not stripped_line.endswith(';'):
            errors.append(f"Declaración de variable mal formada en la línea {i + 1}: {line}")

    if do_count > 0:
        errors.append("DO sin correspondiente ENDDO.")
    if while_count > 0:
        errors.append("WHILE sin correspondiente ENDWHILE.")

    if not errors:
        return "Sintaxis correcta"
    else:
        return " ".join(errors)

def analyze_semantic(code):
    errors = []

    declared_vars = set()
    lines = code.split('\n')

    for i, line in enumerate(lines):
        line = line.strip()

        # Verificar la inicialización de variables
        if re.match(r'\bint\s+[a-zA-Z_][a-zA-Z_0-9]*\s*=\s*\d+\s*;', line):
            var_name = line.split()[1].split('=')[0].strip()
            declared_vars.add(var_name)
        # Verificar el uso de variables antes de la declaración
        elif re.match(r'[a-zA-Z_][a-zA-Z_0-9]*\s*=\s*.*', line):
            var_name = line.split('=')[0].strip()
            if var_name not in declared_vars:
                errors.append(f"Variable {var_name} usada antes de ser declarada en la línea {i + 1}: {line}")
            else:
                # Verificar que todas las variables en el lado derecho de la asignación estén declaradas
                right_side_vars = re.findall(r'[a-zA-Z_][a-zA-Z_0-9]*', line.split('=')[1])
                for var in right_side_vars:
                    if var not in declared_vars and not var.isdigit():
                        errors.append(f"Variable {var} usada antes de ser declarada en la línea {i + 1}: {line}")

    if not errors:
        return "Uso correcto de las estructuras semánticas"
    else:
        return " ".join(errors)

@app.route('/', methods=['GET', 'POST'])
def index():
    code = ''
    lexical_results = []
    total_results = {'KEYWORD': 0, 'ID': 0, 'NUM': 0, 'SYM': 0, 'ERR': 0}
    syntactic_result = ''
    semantic_result = ''
    if request.method == 'POST':
        code = request.form['code']
        lexical_results, total_results = analyze_lexical(code)
        syntactic_result = analyze_syntactic(code)
        semantic_result = analyze_semantic(code)
    return render_template_string(html_template, code=code, lexical=lexical_results, total=total_results, syntactic=syntactic_result, semantic=semantic_result)

if __name__ == '__main__':
    app.run(debug=True)
