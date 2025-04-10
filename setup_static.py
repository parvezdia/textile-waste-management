import os

def create_static_dirs():
    # Base directories
    static_dirs = [
        'static/designs/img_recognition',
        'static/inventory/img_recognition',
        'static/js/img_recognition',
        'static/css',
        'static/img',
    ]

    # Create each directory
    for dir_path in static_dirs:
        full_path = os.path.join(os.path.dirname(__file__), dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"Created directory: {full_path}")

    # Create placeholder files to maintain directory structure
    placeholder_files = [
        'static/designs/img_recognition/.gitkeep',
        'static/inventory/img_recognition/.gitkeep',
        'static/js/img_recognition/.gitkeep',
    ]

    for file_path in placeholder_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        with open(full_path, 'w') as f:
            pass
        print(f"Created placeholder: {full_path}")

if __name__ == '__main__':
    create_static_dirs()