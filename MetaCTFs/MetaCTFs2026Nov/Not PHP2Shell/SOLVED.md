# MetaCTFs 2026 Nov - Not PHP2Shell (solved)

Service: https://e89b09dc80a6ac10.live.sbhost.io (nginx -> php-fpm)

FLAG: SkillBit{p4tch3d_php_bu7_wh4t_4b0u7_th3_c0d3}

## Mechanism
PHPSESSID cookie = base64(serialize(new ArticleModel)) with attacker-controlled
->file. models/ArticleModel.php has __destruct{ readfile($this->file); } and
index.php does `unset($page)` to release it, so the destructor runs and reads any
path the php-fpm worker can open. Arbitrary file read, no auth.

Payload: O:12:"ArticleModel":2:{s:4:"file";s:N:"<path>";s:4:"slug";s:8:"overview";}
Cookie: PHPSESSID=base64(payload)

/flag.txt (root:www-data 0640, outside webroot) -> flag.

## Extra attack surface (not needed)
index.php spl_autoload_register builds `include_once __DIR__."/models/$name.php"`
for any unserialized class ending in "Model" (else __DIR__."/$name.php") - class-name
controlled include, the classic object-injection LFI->RCE gadget chain if a
writable/controlled include source exists.
