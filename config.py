# config.py — EA-MiniGrid-Bench
# Central place for the project root path.
#
# Edit PROJECT_ROOT to point at the folder containing GHI.tif and the
# Raw_Data_<Country>/ subfolders (see the expected layout in README.md).
#
# Examples:
#   Local:        PROJECT_ROOT = "./EA_MiniGrid_Project/"
#   Google Colab: PROJECT_ROOT = "/content/drive/MyDrive/EA_MiniGrid_Project/"

PROJECT_ROOT = "./EA_MiniGrid_Project/"

# The GHI raster is a single global file shared across all four countries.
SOLAR_FILE = PROJECT_ROOT + "GHI.tif"
