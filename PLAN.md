# Plan

## The idea

The user will be able to CRUD poses, characters with their LoRAs, emotions etc and then combine them using a DSL language that will create json structure to create a batch of images.
```json
{
  comfyui_id: <the ID of comfyui host that will run the workflow>
  workflow_id: <the ID of the workflow>
  process: [
    {
      group_ids: [<the id of group>],  
      exclude_item_ids: [<the items that you want to exclude>]
      only_item_ids: [<the items that only those you want to use>]
    },
    {
      group_ids: [<the id of group>],
      exclude_item_ids: [<the items that you want to exclude>]
      only_item_ids: [<the items that only those you want to use>]
    }
  ]
}
```





## Models
- Server 
  - id
  - name
  - host
  - is_local

- Category
  - id
  - name 

- workflow
  - id
  - name 
  - code_name
  - workflow_json
  - load_image_title   string (the title of the LoadImage node in the workflow to upload the reference image) or null
  - save_image_title   string (the title of the SaveImage node in the workflow to download the generated image)
  
- group
  - id 
  - inside_group_id
  - name 
  - code_name
  - category_id
  - use_loras
  - use_controlnet
  
- item
  - id
  - group_id
  - code_name
  - positive_prompt
  - negative_prompt
  - lora_json            or null
  - reference_image 
  
- project
  - id 
  - name 

- process
  - id
  - project_id
  - order_id
  - code_json
  
- result
  - id 
  - project_id
  - process_id
  - process_json  (the exact process of items used to create the specific image)
  - image_path 


## UI Pages
- Servers Page
  - show table of comfyui servers and their status
  - next to each row is delete button
  - add button
      - open a window to add a comfyui server 
      
- Categories Page
