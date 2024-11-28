"""
title: Recraft AI Pipeline
author: Akatsuki.Ryu
author_url: https://github.com/akatsuki-ryu
sponsor: Digitalist Open Tech
date: 2024-11-26
version: 1.0
license: MIT
description: Integrate Recraft AI Image Generation API
requirements: pydantic, openai
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from openai import OpenAI
import os
import re
from difflib import get_close_matches

class Pipeline:
    class Valves(BaseModel):
        RECRAFT_API_TOKEN: str

    def __init__(self):
        self.name = "Recraft AI Pipeline"
        self.valves = self.Valves(RECRAFT_API_TOKEN=os.getenv("RECRAFT_API_TOKEN", ""))
        self.client = None
        self.available_styles = [
            "realistic_image",
            "digital_illustration",
            "vector_illustration",
            "icon",
            "digitalist-color",  # Add custom style to available styles
            "digitalist-style"
        ]
        self.style_substyles = {
            "realistic_image": [
                "b_and_w",
                "enterprise",
                "evening_light",
                "faded_nostalgia",
                "forest_life",
                "hard_flash",
                "hdr",
                "motion_blur",
                "mystic_naturalism",
                "natural_light",
                "natural_tones",
                "organic_calm",
                "real_life_glow",
                "retro_realism",
                "retro_snapshot",
                "studio_portrait",
                "urban_drama",
                "village_realism",
                "warm_folk"
            ],
            "digital_illustration": [
                "2d_art_poster",
                "2d_art_poster_2",
                "engraving_color",
                "grain",
                "hand_drawn",
                "hand_drawn_outline",
                "handmade_3d",
                "infantile_sketch",
                "pixel_art",
                "antiquarian",
                "bold_fantasy",
                "child_book",
                "child_books",
                "cover",
                "crosshatch",
                "digital_engraving",
                "expressionism",
                "freehand_details",
                "grain_20",
                "graphic_intensity",
                "hard_comics",
                "long_shadow",
                "modern_folk",
                "multicolor",
                "neon_calm",
                "noir",
                "nostalgic_pastel",
                "outline_details",
                "pastel_gradient",
                "pastel_sketch",
                "pop_art",
                "pop_renaissance",
                "street_art",
                "tablet_sketch",
                "urban_glow",
                "urban_sketching",
                "vanilla_dreams",
                "young_adult_book",
                "young_adult_book_2"
            ],
            "vector_illustration": [
                "bold_stroke",
                "chemistry",
                "colored_stencil",
                "contour_pop_art",
                "cosmics",
                "cutout",
                "depressive",
                "editorial",
                "emotional_flat",
                "engraving",
                "infographical",
                "line_art",
                "line_circuit",
                "linocut",
                "marker_outline",
                "mosaic",
                "naivector",
                "roundish_flat",
                "segmented_colors",
                "sharp_contrast",
                "thin",
                "vector_photo",
                "vivid_shapes"
            ]
        }

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        self.client = OpenAI(
            base_url='https://external.api.recraft.ai/v1',
            api_key=self.valves.RECRAFT_API_TOKEN
        )

    def create_custom_style(self):
        """Create a custom style using reference images."""
        try:
            # Hardcoded reference image path - replace with your actual image path
            reference_image_path = "/app/./pipelines/reference_image.jpg"
            
            style = self.client.post(
                path='/styles',
                cast_to=object,
                options={'headers': {'Content-Type': 'multipart/form-data'}},
                body={'style': 'digital_illustration'},
                files={'file': open(reference_image_path, 'rb')},
            )
            
            if style and 'id' in style:
                print(f"Created custom style with ID: {style['id']}")
                return style['id']
            else:
                print("Failed to create custom style")
                return None
                
        except Exception as e:
            print(f"Error creating custom style: {str(e)}")
            return None

    async def on_shutdown(self):    
        print(f"on_shutdown:{__name__}")

    def get_style_and_substyle(self, input_text: str) -> tuple[str, str | None]:
        """
        Find the best matching style and substyle from a single input.
        Returns a tuple of (style, substyle) where substyle may be None.
        """
        input_text = input_text.lower()
        
        # First try to match the main style
        style_map = {s.lower(): s for s in self.available_styles}
        style_matches = get_close_matches(input_text, style_map.keys(), n=1, cutoff=0.6)
        
        # Create a map of all substyles to their parent styles
        substyle_to_style = {}
        for style, substyles in self.style_substyles.items():
            for substyle in substyles:
                substyle_to_style[substyle.lower()] = (style, substyle)
        
        # Try to match substyle
        substyle_matches = get_close_matches(input_text, substyle_to_style.keys(), n=1, cutoff=0.6)
        
        # If we found a style match
        if style_matches:
            matched_style = style_map[style_matches[0]]
            # If this style has substyles, try to find a default or matching substyle
            if matched_style in self.style_substyles:
                # If we also found a substyle match and it belongs to this style, use it
                if substyle_matches and substyle_to_style[substyle_matches[0]][0] == matched_style:
                    return matched_style, substyle_to_style[substyle_matches[0]][1]
                # Otherwise return None for substyle
                return matched_style, None
            return matched_style, None
        
        # If we found a substyle match, use its parent style
        if substyle_matches:
            style, substyle = substyle_to_style[substyle_matches[0]]
            return style, substyle
        
        # Default to realistic_image with no substyle
        return "realistic_image", None

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        try:
            # Extract style/substyle specification from prompt if provided in [text] format
            style_match = re.search(r'\[(.*?)\]', user_message)
            
            # Get style and substyle from the input text
            if style_match:
                selected_style, selected_substyle = self.get_style_and_substyle(style_match.group(1))
                print(f"Matched style: {selected_style}, substyle: {selected_substyle}")
            else:
                selected_style, selected_substyle = "realistic_image", None
            
            # Clean the prompt by removing all bracketed content
            clean_prompt = re.sub(r'\[.*?\]', '', user_message).strip()
            
            # Select model based on style
            model = 'recraft20b' if selected_style == 'icon' else 'recraftv3'
            
            # Handle custom style creation if digitalist is requested
            style_id = None
            if selected_style == 'digitalist-style':
                print("Creating custom style for digitalist")
                style_id = self.create_custom_style()
                if not style_id:
                    print("Falling back to realistic style")
                    selected_style = 'realistic_image'
            
            # Prepare request parameters
            params = {
                'prompt': clean_prompt,
                'size': '1280x1024',
                'model': model,
            }

            # add style if the style input is not digitalist
            if selected_style != 'digitalist-style':
                params['style'] = selected_style
            
            # Add substyle if specified and valid
            if selected_substyle:
                params['extra_body'] = {'substyle': selected_substyle}
            elif selected_style == 'digitalist-style' and style_id:
                params['extra_body'] = {
                    'style_id': style_id,
                    # 'controls': {
                    #     'image_type': 'realistic_image',
                    #     'colors': [
                    #         {'rgb': [244, 154, 193]}
                    #     ]
                    # }
                }
            elif selected_style == 'digitalist-color':
                params['style'] = 'realistic_image'
                params['extra_body'] = {
                    # 'style_id': style_id,
                    'controls': {
                        'image_type': 'realistic_image',
                        'colors': [
                            {'rgb': [244, 154, 193]}
                        ]
                    }
                }

            
            response = self.client.images.generate(**params)
            print(response)

            if response and response.data and len(response.data) > 0:
                image_url = response.data[0].url
                message = f"![image]({image_url})\n"
                return message
            else:
                return "No image was generated in the response."

        except Exception as e:
            return f"Error generating image: {str(e)}"
