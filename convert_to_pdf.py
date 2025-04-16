import markdown
import os
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# Read the markdown file
with open('mikrotik_setup_guide.md', 'r') as f:
    md_content = f.read()

# Convert markdown to HTML
html_content = markdown.markdown(md_content, extensions=['extra'])

# Create the HTML document with a proper structure and styling
html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>MikroTik Router Configuration Guide</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 2em;
            color: #333;
        }}
        h1 {{
            color: #0066cc;
            text-align: center;
            margin-bottom: 1em;
            padding-bottom: 0.5em;
            border-bottom: 1px solid #eee;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 1.5em;
            padding-bottom: 0.3em;
            border-bottom: 1px solid #eee;
        }}
        h3 {{
            color: #444;
            margin-top: 1em;
        }}
        strong {{
            color: #0066cc;
        }}
        ol, ul {{
            margin-left: 1em;
        }}
        li {{
            margin-bottom: 0.5em;
        }}
        .footer {{
            text-align: center;
            margin-top: 2em;
            font-size: 0.8em;
            color: #666;
            border-top: 1px solid #eee;
            padding-top: 1em;
        }}
        @page {{
            margin: 2.5cm 1.5cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
    <div class="footer">
        <p>Generated for WiFi Captive Portal Authentication System - {os.environ.get('REPL_SLUG', 'MikroTik Integration')}</p>
    </div>
</body>
</html>
"""

# Configure fonts
font_config = FontConfiguration()

# Create the PDF
HTML(string=html_doc).write_pdf(
    'mikrotik_setup_guide.pdf',
    stylesheets=[],
    font_config=font_config
)

print("PDF created successfully: mikrotik_setup_guide.pdf")