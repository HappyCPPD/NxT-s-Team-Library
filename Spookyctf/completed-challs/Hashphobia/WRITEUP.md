# Hashphobia

Flag: `spooky{a1way5_h45h_5u5_f1les_4nd_ch3ck_review5}`

1. On VirusTotal the hash is case-telemetry.sh. The sandbox preview shows it only runs `curl http://18.117.181.107/`.
2. The server replies `status=nah; message=what's the magic word?`.
3. A VT comment by thehackerguy (Frank C, the challenge author) gives the second half as base64: NG5kX2NoM2NrX3JldmlldzV9 -> `4nd_ch3ck_review5}`.
4. The magic word goes in a header named after the response field: `curl -H 'message: please' http://18.117.181.107/`
 -> `status=ok; payload=c3Bvb2t5e2Exd2F5NV9oNDVoXzV1NV9mMWxlc18=` -> `spooky{a1way5_h45h_5u5_f1les_`. The value isn't case-sensitive. ffuf on header names found it.
