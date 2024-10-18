# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'dataspaces'
copyright = '2024, Yuri Chernushenko'
author = 'Yuri Chernushenko'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
html_use_index = True
html_baseurl = "https://dataspaces.dev"

html_css_files = [
    'https://dataspaces.dev/_static/pygments.css',
    'https://dataspaces.dev/_static/basic.css',
    'https://dataspaces.dev/_static/alabaster.css',
]

html_js_files = [
    'https://dataspaces.dev/_static/documentation_options.js',
    'https://dataspaces.dev/_static/doctools.js',
    'https://dataspaces.dev/_static/sphinx_highlight.js',
]
