import pandas as pd
import geopandas as gpd
import fiona
from xml.etree import ElementTree as ET
import os
from langchain_groq import chat_models
from langchain.tools import tool

## Class to read data
class InspectData:
    def __init__(self,file,xml_file):
        self.file = file
        self.xml_file = xml_file
    
    def inspect_geodata(self):
        layers=fiona.listlayers(self.file)
        
        results={}
        for layer_name in layers:
            
            #read the tables in gdb
            gdf=gpd.read_file(self.file,layer=layer_name)
            
            results[layer_name]={
                "Geometry": gdf.geometry.type.unique().tolist(),
                "Num Rows": len(gdf),
                "Columns": gdf.columns.tolist(),
                "Crs": str(gdf.crs),
            }
            
        
        return results
    
    
    def inspect_csv_file(self):
        try:
            df= pd.read_csv(self.file,encoding="utf-8")
        except UnicodeDecodeError:
            df=pd.read_csv(self.file,encoding="latin-1")
        return {
            "Num Rows": len(df),
            "Columns": df.columns.tolist(),
        }
    
    
    # function to inspect file type
    def inspect_file_type(self):
        if self.file.endswith('.gdb'):
            return self.inspect_geodata()
        
        elif self.file.endswith('.csv'):
            return self.inspect_csv_file()
        
        else:
            return "Unsupported file type"
    
    def read_xml_metadata(self):
        """
        Reads XML metadata from file or folder stored in self.xml_file
        Attempts to parse, falls back to raw XML if structure differs.

        Returns:
            If file: list of field dicts or raw XML string
            If folder: dict {filename: field data or raw XML}
        """
        
        if os.path.isfile(self.xml_file):
            return self._parse_single_xml(self.xml_file)
        
        elif os.path.isdir(self.xml_file):
            results = {}
            for filename in os.listdir(self.xml_file):
                if filename.endswith('.xml'):
                    xml_path = os.path.join(self.xml_file, filename)
                    results[filename] = self._parse_single_xml(xml_path)
            return results
        
        else:
            raise ValueError(f"Path does not exist: {self.xml_file}")
    
    def _parse_single_xml(self, xml_file):
        """Parse single XML file"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            attributes = []
            
            for attr in root.findall('.//attr'):
                attrlabl = attr.find('attrlabl')
                if attrlabl is None:
                    continue
                
                field_name = attrlabl.text
                
                attrdef = attr.find('attrdef')
                definition = attrdef.text if attrdef is not None else ""
                
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
            
            if attributes:
                return attributes
            else:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    return f.read()
        
        except Exception:
            with open(xml_file, 'r', encoding='utf-8') as f:
                return f.read()
        





source={}
## create object for each file
## read the dbg files and xml files

indopac=InspectData('Data/INDOPAC_GIS.gdb','Data/SI_INDOPAC_GIS_Data-Level_Metadata')
indopac_gdb=indopac.inspect_file_type()
indopac_xml=indopac.read_xml_metadata()

source["INDOPAC"]={"GDB": indopac_gdb,
                   "XML": indopac_xml}




africa=InspectData('Data/Africa_GIS.gdb','Data/Africa_GIS_Metadata.xml')
africa_gdb=africa.inspect_file_type()
africa_xml=africa.read_xml_metadata()

source["Africa"]={"GDB":africa_gdb,
                  "XML": africa_xml}



chn=InspectData('Data/CHN_GIS.gdb','Data/SI_CHN_GIS_Data-Level_Metadata')
chn_gdb=chn.inspect_file_type()
chn_xml=chn.read_xml_metadata()

source["CHN"]={"GDB":chn_gdb,
                  "XML": chn_xml}




swasia=InspectData('Data/SWAsia_GIS.gdb','Data/SI_SWAsia_GIS_Data-Level_Metadata')
swasia_gdb=swasia.inspect_file_type()
swasia_xml=swasia.read_xml_metadata()

source["SWAsia"]={"GDB":swasia_gdb,
                  "XML": swasia_xml}



LAC_explore=InspectData('Data/EXPLORE_LAC.csv','Data/EXPLORE_LAC.xml')
lac_ex_csv=LAC_explore.inspect_file_type()
lac_ex_xml=LAC_explore.read_xml_metadata()

source["EXPLORE_LAC"]={"CSV":lac_ex_csv,
                  "XML": lac_ex_xml}


LAC_ports=InspectData('Data/PORTS_LAC.csv','Data/PORTS_LAC.xml')
lac_ports_csv=LAC_ports.inspect_file_type()
lac_ports_xml=LAC_ports.read_xml_metadata()

source["PORTS_LAC"]={"CSV":lac_ports_csv,
                  "XML": lac_ports_xml}



LAC_minefac=InspectData('Data/MINFAC_LAC.csv','Data/1 FINAL MINFAC_LAC.xml')
lac_minefac_csv=LAC_minefac.inspect_file_type()
lac_minefac_xml=LAC_minefac.read_xml_metadata()

source["MINEFAC_LAC"]={"CSV":lac_minefac_csv,
                  "XML": lac_minefac_xml}


print(source)




    