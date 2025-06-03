# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pathlib import Path

# -- Path setup --------------------------------------------------------------

# Add the project root to the Python path so Sphinx can import the modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Automation Agents'
copyright = '2024, Automation Agents Team'
author = 'Automation Agents Team'
release = '1.0.0'
version = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Automatic documentation from docstrings
    'sphinx.ext.autosummary',       # Generate summary tables
    'sphinx.ext.viewcode',          # Add links to highlighted source code
    'sphinx.ext.napoleon',          # Support for NumPy and Google style docstrings
    'sphinx.ext.intersphinx',       # Link to other project's documentation
    'sphinx.ext.todo',              # Support for todo items
    'sphinx.ext.coverage',          # Coverage extension
    'sphinx.ext.githubpages',       # GitHub Pages support
    'myst_parser',                  # Support for Markdown files
]

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Type hints
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'pydantic': ('https://docs.pydantic.dev/', None),
    'asyncio': ('https://docs.python.org/3/library/asyncio.html', None),
}

templates_path = ['_templates']
exclude_patterns = []

# Support for Markdown
source_suffix = {
    '.rst': None,
    '.md': 'myst_parser',
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Custom CSS
html_css_files = [
    'custom.css',
]

# HTML context
html_context = {
    'display_github': True,
    'github_user': 'automation-agents',
    'github_repo': 'automation-agents',
    'github_version': 'main',
    'conf_py_path': '/docs_sphinx/source/',
}

# -- Options for todo extension ----------------------------------------------

todo_include_todos = True

# -- Mock imports for modules that might not be available during doc build --

autodoc_mock_imports = [
    'chromadb',
    'pydantic_ai',
    'rich',
    'openai',
    'PIL',
    'yaml',
    'requests',
]

# -- Custom settings --

# Don't show module names in the documentation
add_module_names = False

# Show typehints in the signature
autodoc_typehints_format = 'short'