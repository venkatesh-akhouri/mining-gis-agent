import pandas as pd
import geopandas as gpd
import fiona

## Class to read data
class InspectData:
    def __init__(self,file):
        self.file = file
    
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
        
        



#create objects for geodata
indopac=InspectData("Data/INDOPAC_GIS.gdb").inspect_file_type()
sw_asia=InspectData("Data/SWAsia_GIS.gdb").inspect_file_type()
chn=InspectData("Data/CHN_GIS.gdb").inspect_file_type()
africa=InspectData("Data/Africa_GIS.gdb").inspect_file_type()
lac_ports=InspectData("Data/PORTS_LAC.csv").inspect_csv_file()
lac_exploration=InspectData("Data/EXPLORE_LAC.csv").inspect_csv_file()
lac_facilities=InspectData("Data/MINFAC_LAC.csv").inspect_csv_file()




print("*"*50)
print("Indopac")
print(indopac)

print("*"*50)
print("sw_asia")
print(sw_asia)

print("*"*50)
print("chn")
print(chn)

print("*"*50)
print("Africa")
print(africa)

print("*"*50)
print("lac_ports")
print(lac_ports)



    