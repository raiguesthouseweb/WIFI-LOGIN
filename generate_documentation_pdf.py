#!/usr/bin/env python3
"""
Generate colorful PDF documentation from Markdown
"""
import os
import logging
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def markdown_to_pdf(markdown_file, pdf_file):
    """
    Convert Markdown file to PDF with styling
    
    Args:
        markdown_file (str): Path to markdown file
        pdf_file (str): Path to output PDF file
    """
    logger.info(f"Converting {markdown_file} to {pdf_file}")
    
    # Read markdown content
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.attr_list'
        ]
    )
    
    # Add HTML wrapper
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>MikroTik Captive Portal Documentation</title>
        <style>
            {markdown_content.split('<style>')[1].split('</style>')[0]}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Setup font configuration
    font_config = FontConfiguration()
    
    # Convert HTML to PDF
    html = HTML(string=html_doc)
    
    # Generate PDF
    html.write_pdf(pdf_file, font_config=font_config)
    logger.info(f"PDF successfully generated: {pdf_file}")

if __name__ == "__main__":
    markdown_file = "project_documentation.md"
    pdf_file = "MikroTik_Captive_Portal_Documentation.pdf"
    
    if not os.path.exists(markdown_file):
        logger.error(f"Markdown file not found: {markdown_file}")
        exit(1)
    
    markdown_to_pdf(markdown_file, pdf_file)
    logger.info("PDF generation completed successfully")