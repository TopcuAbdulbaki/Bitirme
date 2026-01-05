"""
Proto Compilation Script
Run this from the project root to compile proto files for all nodes.
"""
import os
import subprocess
import shutil

# Nodes that need proto files
NODES = ['orchestrator', 'crawler', 'db', 'vlm', 'llm']

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROTO_FILE = os.path.join(PROJECT_ROOT, 'proto', 'orchestrator.proto')


def compile_for_node(node_name: str):
    """Compile proto file for a specific node."""
    node_dir = os.path.join(PROJECT_ROOT, node_name if node_name != 'db' else 'Db')
    proto_dir = os.path.join(node_dir, 'proto')
    generated_dir = os.path.join(node_dir, 'generated')
    
    # Create directories
    os.makedirs(proto_dir, exist_ok=True)
    os.makedirs(generated_dir, exist_ok=True)
    
    # Copy proto file to node
    dest_proto = os.path.join(proto_dir, 'orchestrator.proto')
    shutil.copy2(PROTO_FILE, dest_proto)
    print(f"  Copied proto to {node_name}/proto/")
    
    # Create __init__.py in generated folder
    init_file = os.path.join(generated_dir, '__init__.py')
    with open(init_file, 'w') as f:
        f.write('# Auto-generated gRPC code\n')
    
    # Compile proto
    cmd = [
        'python', '-m', 'grpc_tools.protoc',
        f'-I{proto_dir}',
        f'--python_out={generated_dir}',
        f'--grpc_python_out={generated_dir}',
        dest_proto
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✅ Compiled proto for {node_name}")
        
        # Fix imports in generated files (grpc_tools generates absolute imports)
        fix_imports(generated_dir)
        return True
    else:
        print(f"  ❌ Failed to compile for {node_name}: {result.stderr}")
        return False


def fix_imports(generated_dir: str):
    """Fix relative imports in generated gRPC files."""
    grpc_file = os.path.join(generated_dir, 'orchestrator_pb2_grpc.py')
    
    if os.path.exists(grpc_file):
        with open(grpc_file, 'r') as f:
            content = f.read()
        
        # Fix import statement
        content = content.replace(
            'import orchestrator_pb2 as orchestrator__pb2',
            'from . import orchestrator_pb2 as orchestrator__pb2'
        )
        
        with open(grpc_file, 'w') as f:
            f.write(content)
        print(f"  Fixed imports in generated files")


def main():
    print("=" * 50)
    print("Proto Compilation for All Nodes")
    print("=" * 50)
    
    # Check if proto file exists
    if not os.path.exists(PROTO_FILE):
        print(f"❌ Proto file not found: {PROTO_FILE}")
        return
    
    success_count = 0
    for node in NODES:
        print(f"\nProcessing {node}...")
        if compile_for_node(node):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"Compilation complete: {success_count}/{len(NODES)} nodes")
    print("=" * 50)


if __name__ == '__main__':
    main()
