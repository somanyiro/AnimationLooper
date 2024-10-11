# Blender Animation Looper

This plugin is built on the foundation of [this article](https://theorangeduck.com/page/creating-looping-animations-motion-capture) by Daniel Holden.

<img src="/images/RunAnimation.gif" width="300"> <img src="/images/RunAnimationLooped.gif" width="300">

## Installation

1. Download the Python script
2. In Blender go to Edit -> Preferences -> Add-ons
3. Click on "Install from Disk"
4. Select the downloaded animation_looper.py file
5. The animation looper panel now should appear under the Edit tab on the right

## How to use

1. Import an animtion into Blender. (Optionally also bring in a model so you can see more than just bones)
2. Cut off the beginning and end so that the animation starts and ends with relatively similar poses
3. Readjust the keyframes so that the animation starts at frame 0
4. Press the "Remove Root Motion" button so that the character stays in place
5. Press the "Loop Animation" button
6. Now you should have a smoothly looping animation
