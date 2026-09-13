import ast
import os
import glob

def get_ast_info(node, source_code):
    lines = source_code.split('\n')
    info = []
    
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper():
                        try:
                            val = ast.unparse(item.value)
                        except:
                            val = "Complex"
                        info.append(f"- **`{target.id}`** = `{val}`")
                        
        elif isinstance(item, ast.FunctionDef):
            args = []
            for arg in item.args.args:
                if item.args.defaults and len(args) >= len(item.args.args) - len(item.args.defaults):
                    # Has default
                    idx = len(args) - (len(item.args.args) - len(item.args.defaults))
                    default_val = ast.unparse(item.args.defaults[idx])
                    args.append(f"{arg.arg}={default_val}")
                else:
                    args.append(arg.arg)
            
            args_str = ", ".join(args)
            info.append(f"### `def {item.name}({args_str})`")
            docstring = ast.get_docstring(item)
            if docstring:
                info.append(f"> {docstring.replace(chr(10), chr(10) + '> ')}\n")
            else:
                info.append(f"*No docstring available.*\n")
                
        elif isinstance(item, ast.ClassDef):
            info.append(f"### `class {item.name}`")
            docstring = ast.get_docstring(item)
            if docstring:
                info.append(f"> {docstring.replace(chr(10), chr(10) + '> ')}\n")
            else:
                info.append(f"*No docstring available.*\n")
                
            for cls_item in item.body:
                if isinstance(cls_item, ast.FunctionDef):
                    args = [a.arg for a in cls_item.args.args]
                    info.append(f"#### `def {cls_item.name}({', '.join(args)})`")
                    mdoc = ast.get_docstring(cls_item)
                    if mdoc:
                        info.append(f"> {mdoc.replace(chr(10), chr(10) + '> ')}\n")
                        
    return "\n".join(info)

def generate():
    os.makedirs("d:/meshroom_test/docs/technical_deep", exist_ok=True)
    for py_file in glob.glob("d:/meshroom_test/*.py"):
        if "generate_docs" in py_file: continue
        
        with open(py_file, 'r', encoding='utf-8') as f:
            code = f.read()
            
        tree = ast.parse(code)
        
        md = f"# `{os.path.basename(py_file)}`\n\n"
        module_doc = ast.get_docstring(tree)
        if module_doc:
            md += f"## Module Overview\n{module_doc}\n\n"
            
        md += "## API Reference\n\n"
        md += get_ast_info(tree, code)
        
        out_name = os.path.basename(py_file).replace('.py', '.md')
        out_path = f"d:/meshroom_test/docs/technical_deep/{out_name}"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(md)
            
if __name__ == '__main__':
    generate()
    print("Done generating deep docs!")

