# This file (html_templates.py) is currently NOT USED by the application.
# The application uses Jinja2 templates loaded from the 'templates/' directory (see main.py).
# This file can be considered deprecated or removed if not intended for future use.

HTML_FORM_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>GitHub Token</title>
    <style>body {{font-family: sans-serif; margin: 20px;}} .container {{max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 5px;}} label, input {{display: block; margin-bottom: 10px;}} input[type="submit"] {{cursor: pointer;}} .error {{color: red;}}</style>
</head>
<body>
    <div class="container">
        <h1>GitHub CV Assistant - Enter Token</h1>
        <p>Enter your GitHub Personal Access Token (PAT) with 'repo' scope.</p>
        {error_message}
        <form method="post" action="/auth/set-token">
            <label for="token">GitHub PAT:</label>
            <input type="password" id="token" name="token" required style="width: 95%;">
            <input type="submit" value="Set Token & List Repos">
        </form>
    </div>
</body>
</html>
"""

HTML_REPO_LIST_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Your Repositories</title>
    <style>body {{font-family: sans-serif; margin: 20px;}} .container {{max-width: 800px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 5px;}} ul {{list-style: none; padding: 0;}} li {{padding: 8px; border-bottom: 1px solid #eee;}} .error {{color: red;}} .action-btn {{ margin: 10px 0; padding: 10px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; display: inline-block;}}</style>
</head>
<body>
    <div class="container">
        <h1>Your GitHub Repositories</h1>
        <p><a href="/" class="action-btn" style="background-color: #6c757d;">&larr; Change Token</a></p>
        {error_message}
        {repo_content}
        <hr>
        <h2>Generate CV Summary</h2>
        <p>This will process up to {max_repos_cv} of your most recently updated repositories to generate CV entries using Gemini. This may take several minutes and consume API quota.</p>
        <form method="post" action="/generate-cv-summary">
            <input type="submit" value="Generate CV Summary from Top Repos" class="action-btn" style="background-color: #28a745;">
        </form>
    </div>
</body>
</html>
"""

HTML_REPO_CONTENT_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>Repo: {repo_full_name}</title>
    <style>body {{font-family: sans-serif; margin: 20px;}} .container {{max-width: 800px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 5px;}} ul {{list-style: none; padding: 0;}} li {{padding: 8px; border-bottom: 1px solid #eee;}} .error {{color: red;}} .nav-link {{ margin-right: 10px; text-decoration: none;}} .path {{background-color: #f0f0f0; padding: 5px; border-radius: 3px; margin-bottom:10px;}}</style>
</head>
<body>
    <div class="container">
        <h1>{repo_full_name}</h1>
        <p><a href="/repos" class="nav-link">&larr; Back to Repositories</a> {up_link}</p>
        <p class="path">Current Path: /{current_path_display}</p>
        {error_message}
        {content_list}
    </div>
</body>
</html>
"""

HTML_FILE_VIEW_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>File: {file_path_display}</title>
    <style>body {{font-family: sans-serif; margin: 20px;}} .container {{max-width: 900px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 5px;}} pre {{background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto;}} .error {{color: red;}} .nav-link {{ margin-right: 10px; text-decoration: none;}}</style>
</head>
<body>
    <div class="container">
        <h1>File: {file_path_display}</h1>
        <p>In Repository: {repo_full_name}</p>
        <p><a href="{back_to_dir_link}" class="nav-link">&larr; Back to Directory</a> <a href="/repos" class="nav-link">&larr; Back to Repositories</a></p>
        {error_message}
        {file_content_display}
    </div>
</body>
</html>
"""

HTML_CV_SUMMARY_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>CV Summary</title>
    <style>
        body {{font-family: sans-serif; margin: 20px;}}
        .container {{max-width: 800px; margin: auto; padding: 20px; border: 1px solid #ccc; border-radius: 5px;}}
        .cv-entry {{margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 4px; background-color: #f9f9f9;}}
        .cv-entry h3 {{margin-top: 0; color: #007bff;}}
        .cv-entry p {{margin-bottom: 5px;}}
        .cv-entry strong {{color: #333;}}
        .error {{color: red; background-color: #ffe0e0; padding: 10px; border-radius: 4px;}}
        .info {{color: green; background-color: #e0ffe0; padding: 10px; border-radius: 4px;}}
        .action-btn {{ margin: 10px 0; padding: 10px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; display: inline-block;}}
    </style>
</head>
<body>
    <div class="container">
        <h1>Generated CV Summaries</h1>
        <p><a href="/repos" class="action-btn">&larr; Back to Repositories</a></p>
        {message}
        {cv_entries_html}
    </div>
</body>
</html>
"""

