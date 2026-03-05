from ij import IJ
from ij.io import DirectoryChooser
from ij.plugin import ChannelSplitter
from ij.gui import GenericDialog
import os
import random

# Ask user which channel is NFH
gd = GenericDialog("Select channel to open")
gd.addNumericField("Which channel would you like to open? (enter channel number)", 1, 0)
gd.showDialog()
if gd.wasCanceled():
    IJ.error("User canceled dialog")
    exit()
nfhChannel = int(gd.getNextNumber())

# Ask user to select a folder
dc = DirectoryChooser("Select a folder with images")
inputDir = dc.getDirectory()
if inputDir is None:
    IJ.error("No folder selected")
    exit()

# Supported image extensions (case insensitive)
extensions = [".ims", ".tif", ".tiff", ".czi", ".lif", ".dcm", ".ome.tif", ".nd2", ".svs"]

# Get list of supported files in folder
matching_paths = [f for f in os.listdir(inputDir) if any(f.lower().endswith(ext) for ext in extensions)]

if len(matching_paths) == 0:
    IJ.error("No supported image files found in the folder.")
    exit()

# Ask how many images to open — with input validation loop
while True:
    n_input = IJ.getString("How many random images to open? (max: {})".format(len(matching_paths)), "1")
    if n_input is None:
        IJ.showMessage("Cancelled", "Operation cancelled by the user.")
        exit()
    try:
        n_to_open = int(n_input)
        if n_to_open <= 0 or n_to_open > len(matching_paths):
            raise ValueError
        break
    except:
        IJ.showMessage("Error", "Please enter a positive number up to {}.".format(len(matching_paths)))

# Randomly sample the images
selected_files = random.sample(matching_paths, n_to_open)

for fileName in selected_files:
    fullPath = os.path.join(inputDir, fileName)
    #IJ.log("Processing: " + fileName)

    # Open image with Bio-Formats
    IJ.run("Bio-Formats Importer", "open=[" + fullPath + "] autoscale color_mode=Composite view=Hyperstack stack_order=XYCZT quiet")

    # Get current image
    imp = IJ.getImage()

    # Split channels
    channels = ChannelSplitter.split(imp)

    # Close original composite
    imp.close()

    # Validate NFH channel number
    if nfhChannel < 1 or nfhChannel > len(channels):
        IJ.log("Invalid channel number for image: " + fileName)
        for chImg in channels:
            chImg.close()
        continue

    # Close all channels except NFH channel
    for i, chImg in enumerate(channels):
        if i != nfhChannel - 1:
            chImg.close()

    # Get NFH channel image
    nfh_img = channels[nfhChannel - 1]

    # Convert to 8-bit
    #IJ.run(nfh_img, "8-bit", "")

    # Show NFH channel image
    nfh_img.show()

#IJ.log("Processing completed.")
