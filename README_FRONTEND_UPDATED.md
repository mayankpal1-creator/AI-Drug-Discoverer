
Frontend updated: added Bootstrap 5 + custom styles (static/css/style.css).
Files modified:
- templates/base.html (linked bootstrap and custom css/js)
- templates/home.html (created if missing)
- templates/login.html, signup.html (created if missing)
- static/css/style.css (new)
- static/js/main.js (new, empty)

What I did:
- Added responsive Bootstrap layout and nicer form styling.
- Wrapped template content blocks in a container/card for attractive look.
- Did NOT change backend logic or database code.

How to run:
1. Unzip and run your Flask app as before, e.g.:
   export FLASK_APP=app.py
   flask run
2. Ensure static folder is served by your Flask app (default).
3. If you had custom base.html names, verify templates extend the modified base.html.

If you want further visual tweaks (dark theme, Tailwind, specific colors), tell me and I'll update.
