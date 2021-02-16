import os, os.path

con = None
media_dir = './media'
template_path = os.getenv('TEMPLATE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_new.html'))
