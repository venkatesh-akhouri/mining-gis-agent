# import fiona
# import geopandas as gpd
#
# # Path to your geodatabase
# gdb_path = "INDOPAC_GIS.gdb"  # UPDATE THIS PATH
#
# print("=" * 50)
# print("EXPLORING GEODATABASE")
# print("=" * 50)
#
# # List all layers
# print("\nLayers in geodatabase:")
# layers = fiona.listlayers(gdb_path)
# for i, layer in enumerate(layers, 1):
#     print(f"{i}. {layer}")
#
# # Inspect each layer
# print("\n" + "=" * 50)
# print("LAYER DETAILS")
# print("=" * 50)
#
# for layer in layers:
#     print(f"\n--- {layer} ---")
#     gdf = gpd.read_file(gdb_path, layer=layer)
#
#     print(f"Geometry type: {gdf.geometry.type.unique()}")
#     print(f"Total features: {len(gdf)}")
#     print(f"Coordinate system: {gdf.crs}")
#     print(f"Columns: {list(gdf.columns)}")
#     print(f"First few rows:")
#     print(gdf.head(2))
#
#
# # import xml.etree.ElementTree as ET
# # from pprint import pprint
# #
# # # Path to one metadata file
# # xml_path = "/Users/venky/mining-gis-agent/SI_INDOPAC_GIS_Data-Level_Metadata/INDOPAC_Mineral_Development.xml"  # UPDATE THIS
# #
# # tree = ET.parse(xml_path)
# # root = tree.getroot()
# #
# # # Print the XML structure
# # pprint(ET.tostring(root, encoding='unicode'))



import sqlite3

#create connection
conn = sqlite3.connect('clean_mining_data.gpkg')

#create cursor
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print(cursor.fetchall())

