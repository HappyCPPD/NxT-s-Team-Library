# Veloren v0.18.0 client build kit

Build your own Veloren client from the official source, change anything you
like, and rebuild in seconds. The kit is two files you drop into your clone of
Veloren:

- `ctf.Dockerfile`: the build tools (Rust and friends) in a container;
- `ctf.sh`: builds the client in that container, then starts it.

Needs: git, Docker, about 15 GB of free disk space, and a Linux desktop with
working Vulkan or OpenGL drivers to play.

## Get started

```sh
git clone --depth 1 --branch v0.18.0 https://gitlab.com/veloren/veloren.git
cd veloren
cp /path/to/ctf.Dockerfile /path/to/ctf.sh .
./ctf.sh
```

The first run prepares the container and builds the whole client. That takes
about 10 minutes on a 12-core machine, longer on a laptop. Then the client
starts. Connect to your Instance's address.

## Change something, try it

Edit any file in the clone, then run `./ctf.sh` again. Only what you changed is
rebuilt, which takes seconds to a minute, and the client starts again.

- `./ctf.sh build` only builds. The client is then at
 `./target/no_overflow/veloren-voxygen`; start it from the clone with
 `VELOREN_ASSETS=./assets ./target/no_overflow/veloren-voxygen`.
- `git diff` shows your changes. The kit's own files stay out of it.
- Everything is written into the clone as your own user: the build output in
 `target/` and downloaded crates in `.ctf/`. Delete them to start over.

## Notes

- The client must be v0.18.0: newer or older clients can't talk to the
 Instance.
- If you cloned without `git-lfs` installed, the game's images, fonts and
 sounds are only placeholders. The kit notices and downloads them (about
 450 MB).
- `no_overflow` is one of upstream's optimised build profiles, without the
 release build's slow link-time optimisation.
- The client is built on Ubuntu 22.04, so it runs on any Linux with glibc 2.35
 or newer.
- Windows: install Docker Desktop with WSL 2, and run the kit inside your WSL
 Linux (Ubuntu); WSLg shows the game window. This is best effort; native
 Windows builds aren't supported by the kit. macOS isn't supported, but you
 can check out the [upstream instructions](https://book.veloren.net/contributors/compiling.html) for building.
