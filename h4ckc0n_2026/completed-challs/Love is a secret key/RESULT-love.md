# RESULT - Love is a secret key (Web, 100 pts, 211 solves)

STATUS: SOLVED
FLAG: d4rk{k4ich0_l0v3s_Sh1n0miy4}

## MECHANISM

Target: https://h4ckc0n-playforge.chals.io/love/ (Flask app behind nginx)

1. Recon: `robots.txt` (served at /love/robots.txt) leaked two hidden routes:
 - Disallow: /internal-notice
 - Disallow: /maintenance

2. `/love/internal-notice` leaked the victim identity + order id:
 - Account username: kaicho
 - Related order: 1337

3. `/love/maintenance` leaked the app config block, including the Flask signing key
 (the "Too tired? Here, drink a flask of water" line = Flask hint):
 ```
 APP_ENV = festival
 SECRET_KEY = love_is_war
 MAINTENANCE_STATUS = nominal
 Last_Check = successful
 ```

4. `/love/track` (POST username=kaicho&order_id=1337) returned the order and revealed a
 gated invoice endpoint: GET /love/invoice/1337 (plus user_id 66066 for kaicho).
 Requesting it anonymously -> 302 to /track with flash
 "Authentication Required. Please login as the respective user before downloading this invoice."

5. Registered/logged in a throwaway account and decoded its Flask session cookie to learn the
 session schema:
 ```json
 {"_flashes":[...],"user_id":66940,"username":"tester4013"}
 ```

6. Forged a Flask session cookie for the victim using the leaked SECRET_KEY (love_forge.py,
 itsdangerous URLSafeTimedSerializer, salt "cookie-session"):
 payload = {"user_id":66066,"username":"kaicho"}

7. Requested the invoice with the forged cookie -> HTTP 200, application/pdf
 (Content-Disposition: attachment; filename="shuchiin-invoice-1337.pdf").

8. `pdftotext love_invoice_1337.pdf -` printed the invoice; the "CONFIDENTIAL ORDER REFERENCE"
 field contains the flag.

## PROOF (actual output)

$ curl -s -i -b "love_session=<forged kaicho cookie>" https://h4ckc0n-playforge.chals.io/love/invoice/1337
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Length: 2273
Content-Disposition: attachment; filename="shuchiin-invoice-1337.pdf"

$ pdftotext love_invoice_1337.pdf -
SHUCHIIN FESTIVAL SUPPLIES
INVOICE #1337
Buyer: president_miyuki
Username: kaicho
Order Status: Dispatched
Product: Crimson Heart Mylar Balloons
Quantity: 100
Tracking ID: woah_a_rezero_mystery
BUYER'S NOTE: Deliver discreetly behind the gym before the festival bonfire. Do NOT let Shinomiya see this.
CONFIDENTIAL ORDER REFERENCE
d4rk{k4ich0_l0v3s_Sh1n0miy4}

## ARTIFACTS
- love_forge.py - Flask cookie forger (itsdangerous, key=love_is_war)
- love_forged_token.txt - forged kaicho session cookie value
- love_invoice_1337.pdf - fetched invoice (raw HTTP response + PDF)
- love_cookies.txt, love_testuser.txt - throwaway test account artifacts
- RESULT-love.md - this file
