# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Cloud Data Stack'
copyright = '2024, Yuri Chernushenko'
author = 'Yuri Chernushenko'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx_rtd_theme']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '_static/logo_text_white.svg'
html_favicon = '_static/logo_white_16x16.png'
html_css_files = [
    'custom.css',
]

html_show_sourcelink = False

html_theme_options = {
    'prev_next_buttons_location': None,
    'style_nav_header_background': '#343131',
    'logo_only': True,
}