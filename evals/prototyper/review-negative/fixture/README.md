# Site gateway

The gateway sits in each warehouse's comms cabinet. It pulls the video from the site's security cameras, and runs motion detection on it, so that only the clips with motion are uploaded to the cloud.

- Hardware: a Raspberry Pi 5 with 8 GB of memory and the official active cooler, on the site's wired network.
- Cameras: each one streams 1080p H.264 video at 15 frames per second to the gateway, over the site's network.
- Software: the `gatewayd` service, written in Go, which decodes each stream with `ffmpeg` and passes every fifth frame to the motion detector.

Today's sites have up to 12 cameras each, and the gateway's processor sits at about 40% on the largest of them. The six sites joining next year have up to 50 cameras each.
