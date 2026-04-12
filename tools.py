import fiona
import geopandas as gpd

def inspect_geodatabase(path):
    '''
    inspects the geodata base and returns structured information
    :param path:
    :return:
    '''
    
    layers=fiona.listlayers(path)
    
    results={}
    for layer_name in layers:
    
        gdf=gpd.read_file(path, layer=layer_name)
        
        results[layer_name] = {
            "geometry_type": gdf.geometry.type.unique().tolist(),
            "row_count": len(gdf),
            "columns": gdf.columns.tolist(),
            "crs": str(gdf.crs)
        }
        
    
    return results


import xml.etree.ElementTree as ET


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


if __name__ == "__main__":
    # Test the function
    # gdb_path = "INDOPAC_GIS.gdb"  # UPDATE THIS
    #
    # result = inspect_geodatabase(gdb_path)
    #
    # # Print results nicely
    # for layer, info in result.items():
    #     print(f"\n{layer}:")
    #     print(f"  Type: {info['geometry_type']}")
    #     print(f"  Rows: {info['row_count']}")
    #     print(f"  Columns: {len(info['columns'])}")
    
    xml_path = "SI_INDOPAC_GIS_Data-Level_Metadata/INDOPAC_Mineral_Development.xml"  # UPDATE THIS
    
    fields = read_xml_metadata(xml_path)
    
    # Print first 5 fields
    for field in fields[:5]:
        print(f"\nField: {field['field_name']}")
        if field['alias']:
            print(f"  Alias: {field['alias']}")
        print(f"  Definition: {field['definition'][:100]}...")
    
    