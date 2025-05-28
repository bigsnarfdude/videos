import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    index_template_path = os.path.join(project_root, 'templates', 'index.html.template')
    output_html_path = os.path.join(project_root, 'index.html')

    with open(index_template_path, 'r') as f:
        index_template_content = f.read()
    
    # Directly write the template content.
    # JavaScript will handle the video card rendering and placeholder.
    final_html = index_template_content 

    with open(output_html_path, 'w') as f:
        f.write(final_html)
    
    print(f"Base index.html generated successfully at {output_html_path}")

if __name__ == '__main__':
    main()
