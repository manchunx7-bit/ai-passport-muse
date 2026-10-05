# Public Muse artwork

`muse_avatar_public_frames.c` is an original geometric robot, MIT licensed,
copied from this project's public Muse port. Its generator is
[tools/generate_avatar.py](https://github.com/manchunx7-bit/ai-passport-muse/blob/main/tools/generate_avatar.py).

This module includes only the original, Flash-resident public frames. The host
firmware must select `muse_avatar_public_frames.c` when integrating the module.
Official Jollybot artwork is not included: the SDK license excludes that art.
Do not add it or its rendering tools to public distributions without separate rights.

The frames use a 30-frame, 64 by 64 RGB565 interface; public playback
does not add a runtime image buffer.
