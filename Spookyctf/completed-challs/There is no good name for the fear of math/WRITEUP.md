# There is no good name for the fear of math

Flag (decrypted plaintext): `spooky_scary_nonassociative_diffie_hellman`

The public value is Ma = a^-1 * g * a. Its 2nd and 3rd parts are linear in a's b and c:
Ma1 = g1*mu^-x + y*(1 - mu^-g0), and the same for Ma2. So for any x you can solve for y and z,
then solve the 4th part for w. The key assoc(a, g, Mb) * mu^-a0 comes out the same for every x,
so any recovered equivalent key works. Run `solve.py` (it needs the functions from chal.py).
