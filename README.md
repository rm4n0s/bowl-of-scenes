# bowl-of-scenes
The software will help organize workflows, prompts and poses in groups for only one goal, to combine them to create images in bulk.


## Description
This software will help you generate images in bulk based on attributes that you want to combine. 

The attributes are grouped and later on used using a mini programming language.
For example, lets imagine you want to create assets for a game where the characters cry on each pose except when they jump.
After adding every attribute you want to use in groups, then you use a mini language to call the "Code name" that you added in the fields

Here is the example in the mini language
```
local_comfyui -$ workflow_for_anime: characters *  poses(~jumping) * emotions(cry)
```
The execution of the above command will produce this json

```json
{
  "server_code_name": "local_comfyui",
  "generator_code_name": "workflow_for_anime",
  "group_selections": [
    {
      "group_code_name": "character",
      "include_only": null,
      "exclude": null
    },
    {
      "group_code_name": "poses",
      "include_only": null,
      "exclude": [
        "jumping"
      ]
    },
    {
      "group_code_name": "emotions",
      "include_only": [
        "sad"
      ],
      "exclude": null
    }
  ]
}```

Then for this json the Bowl-of-Scenes will produce the inputs for the selected workflow and submit them to a queue to produce each image.


## ComfyUI Custom Nodes
( I am not sure which bawl-of-scenes uses, but this is the list of plugins in my comfyui)
- ComfyUI-Unload-Model
- A8R8_ComfyUI_nodes
- ComfyUI_UltimateSDUpscale
- ComfyUI-Advanced-ControlNet
- ComfyUI_IPAdapter_plus
- ComfyUI-Impact-Pack
- ComfyUI-Inspire-Pack
- comfyui_controlnet_aux
- comfyui-prompt-control
