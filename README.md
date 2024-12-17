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

[How to use video](https://youtu.be/R0j3U4BLoeQ)

1. Import an animtion into Blender. (Optionally also bring in a model so you can see more than just bones)
2. Cut off the beginning and end so that the animation starts and ends with relatively similar poses
3. Readjust the keyframes so that the animation starts at frame 0
4. Select the armature
5. Optionally, press the "Remove Root Motion" button, that will make the character stay in place
6. Press the "Loop Animation" button (make sure the correct root bone is selected, on most skeletons this is the "Hips" bone)
7. Now you should have a smoothly looping animation

## Known Issues

- Too large of a difference between the start and end of the animation can lead to unrealistic movements

## To Do

- Implement more algorithm options from the article
- Add setting for the algorithm to only affect the beginning and end of the animation
- Right now the plugin assumes a key exists for every frame, fail saves need to be added for this
- Add cleanup step to remove unnecessary keys after looping

## Support development

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F1F517KH5W)
