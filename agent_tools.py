from langchain.tools import tool
import geopandas as gpd
import pandas as pd
import json
import os

source = None


@tool
def list_regions() -> str:
    """Get list of all regions and their layers"""
    result = {}
    for region, data in source.items():
        if "GDB" in data:
            result[region] = {
                "type": "GDB",
                "layers": list(data["GDB"].keys())
            }
        elif "CSV" in data:
            result[region] = {
                "type": "CSV",
                "layers": ["csv_data"]
            }
    return json.dumps(result, indent=2)



@tool
def read_layer_data(region: str, layer: str) -> str:
    """Get detailed schema and XML for ONE specific layer"""
    if region not in source:
        return f"Error: Region {region} not found"
    
    data = source[region]
    summary = {
        "region": region,
        "layer": layer,
        "columns": [],
        "xml_definitions": {}
    }
    
    # Get the layer's columns
    if "GDB" in data:
        if layer not in data["GDB"]:
            return f"Error: Layer {layer} not found in {region}"
        layer_info = data["GDB"][layer]
        summary["columns"] = layer_info["Columns"]
        summary["num_rows"] = layer_info.get("Num Rows")
        summary["geometry"] = layer_info.get("Geometry")
    
    elif "CSV" in data:
        summary["columns"] = data["CSV"]["Columns"]
        summary["num_rows"] = data["CSV"].get("Num Rows")
    
    # Find the relevant XML file for this layer
    if data.get("XML"):
        # Check if XML is a dict or list
        xml_data = data["XML"]
        
        if isinstance(xml_data, dict):
            # Look for XML file matching this layer name
            for xml_file, definitions in xml_data.items():
                if layer in xml_file:
                    summary["xml_definitions"] = definitions
                    break
        elif isinstance(xml_data, list):
            # XML is already a list of definitions
            summary["xml_definitions"] = xml_data
    
    return json.dumps(summary, indent=2)


@tool
def transform_and_save(region: str, layer: str, mapping: str) -> str:
    """Transforms ONE layer from ONE region"""
    
    try:
        # Parse mapping
        column_mapping = json.loads(mapping)
        
        # Check if this region has GDB or CSV
        if 'GDB' in source[region]:
            # Read from .gdb
            file_path = f'Data/{region}_GIS.gdb'
            gdf = gpd.read_file(file_path, layer=layer)
        
        elif 'CSV' in source[region]:
            # Read from .csv
            file_path = f'Data/{layer}.csv'
            df = pd.read_csv(file_path)
            
            # Convert to GeoDataFrame (if has lat/lon)
            # TODO: Add lat/lon detection and geometry creation
            gdf = gpd.GeoDataFrame(df)  # Simplified for now
        
        # Apply the mapping (RENAME COLUMNS)
        gdf = gdf.rename(columns=column_mapping)
        
        # Save as .gpkg
        os.makedirs("output/clean_regions", exist_ok=True)
        output_path = f"output/clean_regions/{region}_{layer}.gpkg"
        gdf.to_file(output_path, driver='GPKG')
        
        return f"✓ Saved {output_path}"
    
    except Exception as e:
        return f"✗ Error transforming {region}/{layer}: {str(e)}"


@tool
def merge_all(file_list: str) -> str:
    """
    Merges all transformed .gpkg files into one unified dataset.

    Args:
        file_list: Comma-separated list of .gpkg file paths

    Returns:
        Status message
    """
    try:
        files = file_list.split(',')
        
        gdfs = []
        for file_path in files:
            file_path = file_path.strip()
            if os.path.exists(file_path):
                gdf = gpd.read_file(file_path)
                gdfs.append(gdf)
        
        # Concatenate all
        unified = gpd.pd.concat(gdfs, ignore_index=True)
        
        # Save unified dataset
        output_path = "output/unified_global.gpkg"
        unified.to_file(output_path, driver='GPKG')
        
        return f"✓ Created unified dataset: {output_path} ({len(unified)} total features)"
    
    except Exception as e:
        return f"✗ Error merging: {str(e)}"