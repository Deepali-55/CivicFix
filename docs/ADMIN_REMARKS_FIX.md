# Admin remarks fix

This update makes the admin status endpoint persist the submitted remark even when the selected status is unchanged. It also displays the saved admin remark on the public tracking result page.

## Apply
1. Stop the currently running Flask server with Ctrl+C.
2. Back up your current `CivicFix_Professional_Project` folder.
3. Extract this ZIP and replace the old project folder with the included `CivicFix_Professional_Project` folder (or copy the updated `app.py` and `templates/track.html` into the existing folder).
4. Keep your existing `civicfix.db` and `uploads` folder if you want to retain your local demo data and uploaded images.
5. Run `python app.py` from the project folder and test Admin > Save Update > Track Complaint.

Automated tests were not executable in the packaging environment because Flask is not installed there. Python syntax compilation passed. Run the test suite on your computer with dependencies installed:
`python -m unittest discover -s tests -v`
