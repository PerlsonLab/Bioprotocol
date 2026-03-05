// Ask the user to select a folder with image files
inputDir = getDirectory("Select the folder with image files");

// Ask the user for the mask channel name
Dialog.create("Mask Information");
Dialog.addString("Enter the name of the channel to be used as mask (e.g., NFH):", "NFH");
Dialog.show();
maskName = Dialog.getString();

// Ask user for channel assignments and processing parameters
Dialog.create("Input Parameters");

Dialog.addNumber("Which channel number is " + maskName + "?", 1);

Dialog.addChoice("Thresholding method", 
    newArray("Default", "Huang", "Intermodes", "IsoData", "Li", "MaxEntropy", "Mean", 
             "MinError(I)", "Minimum", "Moments", "Otsu", "Percentile", "RenyiEntropy", 
             "Shanbhag", "Triangle", "Yen"), "Default");

Dialog.addNumber("Threshold minimum (" + maskName + " channel)", 0);
Dialog.addNumber("Threshold maximum (" + maskName + " channel)", 65535);

Dialog.addNumber("Mean cut-off (0 to 1)", 0.95);

//Dialog.addChoice(molecule + " channel display color", 
    //newArray("Red", "Green", "Blue", "Cyan", "Magenta", "Yellow"), "Magenta");

//Dialog.addChoice(maskName + " channel display color", 
    //newArray("Red", "Green", "Blue", "Cyan", "Magenta", "Yellow"), "Red");

Dialog.show();

maskIndex = Dialog.getNumber();
thresholdMethodMask = Dialog.getChoice();
thresholdMinMask = Dialog.getNumber();
thresholdMaxMask = Dialog.getNumber();
meanCut = Dialog.getNumber();
meanCutMultiplied = meanCut*255;
//moleculeLUT = Dialog.getChoice();
//maskLUT = Dialog.getChoice();

// Define base output folder name
baseOutputDir = inputDir + "binary_" + maskName + "Min" + thresholdMinMask + "Max" + thresholdMaxMask;
outputDir = baseOutputDir;

// Define individual output folders for molecule and NFH channels
//moleculeFolder = outputDir + "/Channel_" + moleculeIndex + "_" + molecule;
maskFolder = outputDir + "/Channel_" + maskIndex + "_" + maskName;
//thresholdFolder = outputDir + "/Mask";

// Check for existing folder and increment suffix if needed
suffix = 1;
while (File.exists(outputDir)) {
    outputDir = baseOutputDir + "_" + suffix;
    suffix++;
}

// Create the final output folder
File.makeDirectory(outputDir);

// Create folders
//File.makeDirectory(moleculeFolder);
File.makeDirectory(maskFolder);
//File.makeDirectory(thresholdFolder);

// Get list of files in folder
fileList = getFileList(inputDir);

// Create pixel metadata CSV file in the output directory
csvHeader = "File,Pixel Width (µm),Pixel Height (µm),Pixel Area (µm^2),Z Step (µm),Unit\n";
csvPath = outputDir + "/pixel_metadata.csv";
File.saveString(csvHeader, csvPath);

// Hide processing
setBatchMode(true);

// Initialize logs
badFileList = "";
deletionLog = "";

// Process each image file
for (i = 0; i < fileList.length; i++) {
    if (endsWith(fileList[i], ".ims") || 
        endsWith(fileList[i], ".tif") || 
        endsWith(fileList[i], ".tiff") || 
        endsWith(fileList[i], ".czi") || 
        endsWith(fileList[i], ".lif") || 
        endsWith(fileList[i], ".dcm") || 
        endsWith(fileList[i], ".ome.tif") || 
        endsWith(fileList[i], ".nd2") || 
        endsWith(fileList[i], ".svs")) {

        inputPath = inputDir + fileList[i];
        run("Bio-Formats Importer", "open=[" + inputPath + "] autoscale color_mode=Composite view=Hyperstack stack_order=XYCZT quiet");

        if (nImages == 0) {
            badFileList += inputPath + "\n";
            continue;
        }

        // Extract file name without extension
        fileName = substring(fileList[i], 0, lastIndexOf(fileList[i], "."));

        // Split channels
        run("Split Channels");

        // Get titles of split images
        imageTitles = newArray(nImages);
        for (j = 0; j < nImages; j++) {
            selectImage(j + 1);
            imageTitles[j] = getTitle();
        }

        // Select NFH channel and duplicate before Gaussian Blur
        selectImage(imageTitles[maskIndex - 1]);
        run("Duplicate...", "title=MASK_original duplicate stack");
        maskOriginalTitle = getTitle();

        // Extract and log calibration data from the duplicated original mask channel
        selectImage(maskOriginalTitle);
        getVoxelSize(width, height, depth, unit);
        pixelArea = width * height;

        // Save pixel metadata line to CSV
        csvLine = fileName + "," + width + "," + height + "," + pixelArea + "," + depth + "," + unit;
        File.append(csvLine, csvPath);

        // Work on blurred copy for mask generation
        selectImage(imageTitles[maskIndex - 1]);
        originalTitle = getTitle();
        //run("8-bit");
        setThreshold(thresholdMinMask, thresholdMaxMask);
        setOption("BlackBackground", true);
        run("Convert to Mask", "method=" + thresholdMethodMask + " background=Dark black create");
        //run("Dilate", "stack");
        //run("Dilate", "stack");
        //run("Divide...", "value=255 stack");
        maskTitle = getTitle();

        // Delete slices from mask channel with a mean higher than user defined and save the mask in a parallel folder
        stackSize = nSlices;
        deletedSlices = newArray(stackSize);
        deletedCountMask = 0;

        for (s = stackSize; s >= 1; s--) {
            selectImage(maskTitle);
            setSlice(s);
            getStatistics(area, mean, min, max);
            //print("Slice " + s + ": mean = " + mean*255);

            if (mean >= meanCutMultiplied) {

                // Delete from original mask
                selectImage(originalTitle);
                setSlice(s);
                run("Delete Slice");
                deletedCountMask++;

                // Delete from original mask
                selectImage(maskTitle);
                setSlice(s);
                run("Delete Slice");
            }
        }

        // Z project: Mask
        selectImage(maskTitle);
        run("Z Project...", "projection=[Max Intensity]");
        //run("8-bit");
        //run(maskLUT);
        saveAs("Tiff", maskFolder + "/" + fileName + "_" + maskName + ".tif");

        // Add slice deletion info to log
        deletionLog += fileName + ": Deleted " + deletedCountMask + " slices from " + maskName + " channel.\n";

        // Close everything
        run("Close All");
    }
}

// Restore display mode
setBatchMode(false);

// Final message
finalMessage = "Masked projections saved to:\n" + outputDir + "\n\n";

if (badFileList != "")
    finalMessage += "The following files could not be opened:\n" + badFileList + "\n";

if (deletionLog != "")
    print("Slice Deletion Summary:\n" + deletionLog);

showMessage("Done", finalMessage);
