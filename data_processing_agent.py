import json
import os
from agent_tools import list_regions, read_layer_data, transform_and_save, merge_all
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import agent_tools
from preprocess_data import source

load_dotenv()
agent_tools.source = source

# Set up LLM for creating mappings only
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

print("=" * 50)
print("STARTING DATA PROCESSING")
print("=" * 50)

# Step 1: Get all regions and layers
regions_data = json.loads(list_regions.invoke({}))
print(f"Found {len(regions_data)} regions")

all_files = []

# Step 2: Process each layer
for region, info in regions_data.items():
    print(f"\n{'=' * 50}")
    print(f"PROCESSING REGION: {region}")
    print(f"{'=' * 50}")
    
    for layer in info["layers"]:
        print(f"\nProcessing {region}/{layer}...")
        
        # Read layer data
        layer_data = read_layer_data.invoke({"region": region, "layer": layer})
        layer_json = json.loads(layer_data)
        
        # Ask LLM to create mapping
        prompt = f"""Based on this layer schema and XML definitions, create a JSON mapping to rename columns.

Layer: {layer}
Columns: {layer_json['columns']}
XML Definitions: {layer_json.get('xml_definitions', {})}

Create a JSON mapping that:
1. Decodes cryptic names using XML (e.g., DsgAttr01 → commodity_1)
2. Keeps clear names as-is (e.g., Country → country)
3. Makes names consistent and lowercase with underscores

Return ONLY valid JSON, nothing else. Format: {{"old_name": "new_name", ...}}
"""
        
        response = llm.invoke(prompt)
        mapping_text = response.content.strip()
        
        # Clean up response (remove markdown code blocks if present)
        if "```json" in mapping_text:
            mapping_text = mapping_text.split("```json")[1].split("```")[0].strip()
        elif "```" in mapping_text:
            mapping_text = mapping_text.split("```")[1].split("```")[0].strip()
        
        # Transform and save
        result = transform_and_save.invoke({
            "region": region,
            "layer": layer,
            "mapping": mapping_text
        })
        
        print(result)
        
        if "✓" in result:
            # Extract file path from result
            file_path = result.split("✓ Saved ")[1].strip()
            all_files.append(file_path)

# Step 3: Merge all files
print(f"\n{'=' * 50}")
print("MERGING ALL FILES")
print(f"{'=' * 50}")

file_list = ",".join(all_files)
merge_result = merge_all.invoke({"file_list": file_list})
print(merge_result)

print(f"\n{'=' * 50}")
print("PROCESSING COMPLETE")
print(f"{'=' * 50}")