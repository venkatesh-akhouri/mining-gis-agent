import fiona
import geopandas as gpd
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv
from groq import Groq
import json

# Load environment variables
load_dotenv()


def inspect_geodatabase(path):
    '''
    Inspects the geodatabase and returns structured information
    :param path: Path to .gdb folder
    :return: Dictionary with layer information
    '''
    
    layers = fiona.listlayers(path)
    
    results = {}
    for layer_name in layers:
        gdf = gpd.read_file(path, layer=layer_name)
        
        results[layer_name] = {
            "geometry_type": gdf.geometry.type.unique().tolist(),
            "row_count": len(gdf),
            "columns": gdf.columns.tolist(),
            "crs": str(gdf.crs)
        }
    
    return results


def read_xml_metadata(xml_path: str) -> list:
    """
    Reads XML metadata and extracts field attribute definitions.

    Args:
        xml_path: Path to the XML metadata file

    Returns:
        List of dictionaries, each containing field info
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Find all attribute definitions
    attributes = []
    
    # XML structure: <eainfo><detailed><attr>
    for attr in root.findall('.//attr'):
        # Get field name
        attrlabl = attr.find('attrlabl')
        if attrlabl is None:
            continue
        
        field_name = attrlabl.text
        
        # Get field definition
        attrdef = attr.find('attrdef')
        definition = attrdef.text if attrdef is not None else ""
        
        # Extract alias from field name if present (e.g., "DsgAttr01 [Alias: Commodity 1]")
        alias = ""
        if '[Alias:' in field_name:
            parts = field_name.split('[Alias:')
            field_name = parts[0].strip()
            alias = parts[1].replace(']', '').strip()
        
        attributes.append({
            'field_name': field_name,
            'alias': alias,
            'definition': definition
        })
    
    return attributes


def create_rename_mapping_with_llm(xml_fields: list, layer_name: str = "") -> dict:
    """
    Uses Groq LLM to intelligently create field name mappings.
    
    Args:
        xml_fields: List of field dictionaries from read_xml_metadata()
        layer_name: Optional layer name for context
        
    Returns:
        Dictionary mapping old_name -> new_name
    """
    
    # Initialize Groq client
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    
    # Prepare field information for the LLM
    fields_text = ""
    for field in xml_fields:
        # Skip system fields
        if field['field_name'] in ['OBJECTID', 'Shape', 'geometry']:
            continue
        
        fields_text += f"\nField: {field['field_name']}\n"
        if field['alias']:
            fields_text += f"Alias: {field['alias']}\n"
        fields_text += f"Definition: {field['definition']}\n"
        fields_text += "---\n"
    
    # Create the prompt
    prompt = f"""You are analyzing GIS field metadata for a mining/mineral resources dataset.

Layer: {layer_name if layer_name else "Mining data"}

Given these field definitions, create a rename mapping that:
- Uses clear, descriptive names based on the DEFINITION and ALIAS
- Uses snake_case (lowercase with underscores)
- Keeps names concise but meaningful (max 3-4 words)
- Makes the purpose of each field immediately clear
- For commodity fields (DsgAttr01-06), use pattern like "commodity_1", "commodity_2"
- Skip system fields (OBJECTID, Shape, geometry)

Fields:
{fields_text}

Return ONLY a valid JSON object (not Python dict). Format:
{{"old_field": "new_field", "another_old": "another_new"}}

No markdown formatting, no explanation, just the JSON object."""

    # Call Groq API
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent output
            max_tokens=2000
        )
        
        # Get the response text
        response_text = response.choices[0].message.content.strip()
        
        # Remove any markdown formatting if present
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        # Parse the JSON
        rename_map = json.loads(response_text)
        
        return rename_map
        
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Fallback to simple alias-based mapping
        return create_simple_rename_mapping(xml_fields)


def create_simple_rename_mapping(xml_fields: list) -> dict:
    """
    Fallback function: Creates a simple rename mapping based on aliases.
    Used if LLM call fails.
    
    Args:
        xml_fields: List of field dictionaries
        
    Returns:
        Dictionary mapping old_name -> new_name
    """
    rename_map = {}
    
    for field in xml_fields:
        old_name = field['field_name']
        alias = field['alias']
        
        # Skip system fields
        if old_name in ['OBJECTID', 'Shape', 'geometry']:
            continue
        
        # Use alias if available, otherwise keep original
        if alias:
            # Clean up: lowercase, replace spaces with underscores
            new_name = alias.lower().replace(' ', '_').replace('(', '').replace(')', '')
            rename_map[old_name] = new_name
        else:
            # Keep original name but lowercase
            rename_map[old_name] = old_name.lower()
    
    return rename_map


def save_geopackage(gdb_path: str, xml_folder: str, output_path: str, rename_mappings: dict = None):
    """
    Reads all layers from geodatabase, renames columns, and saves as GeoPackage.
    
    Args:
        gdb_path: Path to the .gdb folder
        xml_folder: Path to folder containing XML metadata files
        output_path: Path where the .gpkg file will be saved
        rename_mappings: Optional dict of {layer_name: rename_map}
                        If None, will generate mappings using LLM
    
    Returns:
        Dictionary with processing results
    """
    
    results = {
        'layers_processed': [],
        'errors': [],
        'output_file': output_path
    }
    
    # Get all layers
    layers = fiona.listlayers(gdb_path)
    print(f"Found {len(layers)} layers in geodatabase")
    
    for layer_name in layers:
        try:
            print(f"\nProcessing layer: {layer_name}")
            
            # Read the layer
            gdf = gpd.read_file(gdb_path, layer=layer_name)
            print(f"  Rows: {len(gdf)}")
            
            # Get rename mapping for this layer
            if rename_mappings and layer_name in rename_mappings:
                rename_map = rename_mappings[layer_name]
            else:
                # Try to find corresponding XML file
                xml_file = os.path.join(xml_folder, f"{layer_name}.xml")
                
                if os.path.exists(xml_file):
                    print(f"  Reading metadata from: {xml_file}")
                    xml_fields = read_xml_metadata(xml_file)
                    rename_map = create_rename_mapping_with_llm(xml_fields, layer_name)
                else:
                    print(f"  WARNING: No XML file found for {layer_name}, skipping renaming")
                    rename_map = {}
            
            # Rename columns
            if rename_map:
                # Only rename columns that exist in the GeoDataFrame
                valid_renames = {old: new for old, new in rename_map.items() if old in gdf.columns}
                gdf = gdf.rename(columns=valid_renames)
                print(f"  Renamed {len(valid_renames)} columns")
            
            # Save to GeoPackage (append mode after first layer)
            mode = 'w' if len(results['layers_processed']) == 0 else 'a'
            gdf.to_file(output_path, layer=layer_name, driver='GPKG', mode=mode)
            
            results['layers_processed'].append({
                'name': layer_name,
                'rows': len(gdf),
                'columns_renamed': len(rename_map) if rename_map else 0
            })
            
            print(f"  ✓ Saved to GeoPackage")
            
        except Exception as e:
            error_msg = f"Error processing {layer_name}: {str(e)}"
            print(f"  ✗ {error_msg}")
            results['errors'].append(error_msg)
    
    print(f"\n{'='*50}")
    print(f"Processing complete!")
    print(f"Layers processed: {len(results['layers_processed'])}")
    print(f"Errors: {len(results['errors'])}")
    print(f"Output saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    # Test the complete workflow
    
    # Update these paths to match your system
    gdb_path = "INDOPAC_GIS.gdb"
    xml_folder = "SI_INDOPAC_GIS_Data-Level_Metadata"
    output_path = "clean_mining_data.gpkg"
    
    print("="*50)
    print("AGENT 1: DATA PREPARATION")
    print("="*50)
    
    # Test with one layer first
    print("\n--- Testing with one layer ---")
    xml_path = os.path.join(xml_folder, "INDOPAC_Mineral_Development.xml")
    
    if os.path.exists(xml_path):
        print(f"\n1. Reading XML metadata...")
        fields = read_xml_metadata(xml_path)
        print(f"   Found {len(fields)} fields")
        
        print(f"\n2. Creating rename mapping with LLM...")
        rename_map = create_rename_mapping_with_llm(fields, "INDOPAC_Mineral_Development")
        
        print(f"\n3. Proposed column renames:")
        for old, new in list(rename_map.items())[:10]:  # Show first 10
            print(f"   {old:20} -> {new}")
        
        print(f"\n   Total renames: {len(rename_map)}")
    
    # Uncomment below to process ALL layers and create the GeoPackage

    print("\n\n--- Processing all layers ---")
    results = save_geopackage(
        gdb_path=gdb_path,
        xml_folder=xml_folder,
        output_path=output_path
    )

    print("\n\nFINAL RESULTS:")
    print(json.dumps(results, indent=2))
  