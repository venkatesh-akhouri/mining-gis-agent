from langchain.tools import tool
import geopandas as gpd
import pandas as pd
import json
import os

source=None

@tool
def read_data():
    return json.dumps(source,indent=2)


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
            
    
    

